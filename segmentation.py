"""
A modified version of hubconf.py

Modifications:
1. Added a function to detect PPE violation in a video file or video stream
2. Added a function to send email alert with attached image

Modifications made by Anubhav Patrick
Date: 04/02/2023
"""

import time

import torch
import numpy as np
import cv2

# from models.common import DetectMultiBackend
from utils.augmentations import letterbox
from send_mail import prepare_and_send_email
from utils.general import (check_img_size, non_max_suppression, scale_coords)
from utils.plots import Annotator, colors, plot_one_box, save_one_box
from utils.segment.general import process_mask, scale_masks
from utils.segment.plots import plot_masks
from utils.torch_utils import select_device
from models.experimental import attempt_load

# Global Variables
is_email_allowed = False  # when user checks the email checkbox, this variable will be set to True
send_next_email = True  # We have to wait for 10 minutes before sending another email
# NEXT TWO STATEMENTS NEED TO BE CHANGED TO MATCH YOUR SETUP!!!
# set the default email sender and recipient
email_sender = 'hamza2019cs148@abesit.edu.in'
email_recipient = 'hamzaaziz822@gmail.com'
# detections_summary will be used to store the detections summary report
detections_summary = ''

# You can give list of classes to filter by name, Be happy you don't have to put class number. ['train','person' ]
classes_to_filter = []

# ----------------VERY IMPORTANT - CONFIGURATION PARAMETERS----------------
# a dictionary to store options for inference
opt = {
    "weights": "best.pt",  # Path to weights file default weights are for nano model
    "yaml": "data/custom_data.yaml",
    "img-size": 640,  # default image size
    "conf-thres": 0.25,  # confidence threshold for inference.
    "iou-thres": 0.25,  # NMS IoU threshold for inference.
    "device": '0',  # device to run our model i.e. 0 or 0,1,2,3 or cpu
    "classes": classes_to_filter  # list of classes to filter or None
}


def violation_alert_generator(im0, subject='PPE Violation Detected', message_text='A PPE violation is detected'):
    """
    This function will send an email with attached alert image and then wait for 10 minutes before sending another email

    Parameters:
        im0 (numpy.ndarray): The image to be attached in the email
        subject (str): The subject of the email
        message_text (str): The message text of the email

    Returns:
        None
    """

    global send_next_email, email_recipient
    send_next_email = False  # set flag to False so that another email is not sent
    print('Sending email alert to ', email_recipient)
    prepare_and_send_email(email_sender, email_recipient, subject, message_text, im0)
    # wait for 10 minutes before sending another email
    time.sleep(600)
    send_next_email = True


def video_segmentation(conf_=0.25, frames_buffer=None):
    """
    This function will detect violations in a video file or a live stream

    Parameters:
        conf_ (float): Confidence threshold for inference
        frames_buffer (list): A list of frames to be processed

    Returns:
        None
    """

    # Declare global variables to be used in this function
    if frames_buffer is None:
        frames_buffer = []

    global send_next_email
    global is_email_allowed
    global email_recipient
    global detections_summary

    # pop first frame from frames_buffer to get the first frame
    # We encountered a bug in which the first frame was not getting properly processed, so we are popping it out
    while True:
        if len(frames_buffer) > 0:
            _ = frames_buffer.pop(0)
            break

    # empty the GPU cache to free up memory for inference
    torch.cuda.empty_cache()

    frame_count = 0
    tick = time.time()

    # Load Model
    with torch.no_grad():
        weights, imgsz = opt['weights'], opt['img-size']
        device = select_device(opt['device'])
        model = attempt_load(weights=weights, device=device)  # load FP32 model
        stride = int(model.stride.max())  # model stride
        imgsz = check_img_size(imgsz, s=stride)  # check img_size

        # if device is not cpu i.e, it is gpu, convert model to half precision
        half = device.type != 'cpu'
        if half:
            model.half()  # convert model to FP16

        # find names of classes in the model
        names = model.module.names if hasattr(model, 'module') else model.names
        print("Classes: ", names)

        # Run inference one time to initialize the model on a tensor of zeros
        if device.type != 'cpu':
            model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))

        # classes to filter out from the detections
        # We will not be filtering out any class and use all four - safe, unsafe, no-helmet and no-jacket
        classes = None
        if opt['classes']:
            classes = []
            for class_name in opt['classes']:
                classes.append(opt['classes'].index(class_name))

        try:
            # Continuously run inference on the frames in the buffer
            while True:
                # if the frames_buffer is not empty, pop the first frame from the buffer
                if len(frames_buffer) > 0:
                    # pop first frame from frames_buffer
                    img0 = frames_buffer.pop(0)
                    # if the popped frame is None, continue to the next iteration
                    if img0 is None:
                        continue
                    # clear the buffer if it has more than 10 frames to avoid memory overflow
                    if len(frames_buffer) >= 10:
                        frames_buffer.clear()
                else:
                    # buffer is empty, nothing to do
                    continue

                img = letterbox(img0, imgsz, stride=stride)[0]  # resize and pad image
                img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB
                img = np.ascontiguousarray(img)  # convert to contiguous array
                img = torch.from_numpy(img).to(device)
                img = img.half() if half else img.float()  # uint8 to fp16/32
                img /= 255  # 0 - 255 to 0.0 - 1.0

                if len(img.shape) == 3:
                    img = img[None]  # expand for batch dim

                pred, out = model(img, augment=False, visualize=False)
                # print("1_pred: ", pred)
                # print("out: ", out)
                proto = out[1]
                # print("proto: ", proto)

                pred = non_max_suppression(pred, conf_thres=conf_, iou_thres=opt["iou-thres"], labels=0, agnostic=False, max_det=1000, nm=32)
                # print("2: ", pred)

                s = ''
                # Process predictions
                for i, det in enumerate(pred):
                    print("Hamza")
                    # print("det: ", det)
                    annotator = Annotator(img0, line_width=3, example=str(names))

                    if len(det):
                        print("Drishti")
                        masks = process_mask(proto[i], det[:, 6:], det[:, :4], img.shape[2:], upsample=True)  # HWC
                        print("masks: ", masks)

                        # Rescale boxes from img_size to img0 size
                        det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img0.shape).round()
                        print("Priya")

                        # Print results
                        for c in det[:, 5].unique():
                            print("c: ", c)
                            n = (det[:, 5] == c).sum()  # detections per class
                            s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                        print("Riya")
                        # Mask plotting --------------------------------------------------------------------------------
                        mcolors = [colors(int(cls), True) for cls in det[:, 5]]
                        im_masks = plot_masks(img[i], masks, mcolors)  # image with masks shape(imh,imw,3)
                        annotator.im = scale_masks(img.shape[2:], im_masks, img0.shape)  # scale to original h, w
                        # Mask plotting --------------------------------------------------------------------------------

                        # i = 0
                        for *xyxy, conf, cls in reversed(det[:, :6]):
                            print("Hello")
                            c = int(cls)  # integer class
                            label = f'{names[c]} {conf:.2f}'
                            print(label)
                            annotator.box_label(xyxy, label, color=(0, 255, 0))
                            # save_one_box(xyxy, img0, file=f"static/predictions/segment_{i}.jpg")
                            # i += 1
                            plot_one_box(xyxy, img0, label=label, color=(0, 255, 0), line_thickness=3)
                            # img0 = cv2.addWeighted(img0, 0.8, masks, 0.2, 0)

                    frame_count += 1
                    tock = time.time()
                    elapsed_time = tock - tick
                    fps = int(frame_count // elapsed_time)
                    print(f"Processed Frames: {fps}")

                    yield img0

        except Exception as exception:
            print(exception)

    tock = time.time()
    elapsed_time = tock - tick
    fps = frame_count // elapsed_time
    print(fps)
