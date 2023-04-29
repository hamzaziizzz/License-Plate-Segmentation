# syntax=docker/dockerfile:1
  
# Step 1 - Select base docker image
# For GLB and ABESIT DGX, uncomment following lines
FROM nvcr.io/nvidia/pytorch:22.11-py3 
# For building image on local ubuntu system, uncomment following line
#FROM python:3.8-slim-buster 

# Step 2 - Upgrade pip
#Select one of the below option
#For GLB and ABESIT DGX
RUN python3 -m pip install --upgrade pip
# For building image on local ubuntu system, uncomment following line
#RUN pip3 install --upgrade pip

# Step 3 - Set timezone, for updating system in subsequent steps
#https://grigorkh.medium.com/fix-tzdata-hangs-docker-image-build-cdb52cc3360d
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Step 4 - Change work directory in docker image
WORKDIR /License-Plate-Segmentation

# Step 5 - Install additional libraries to work on videos
RUN apt update -y && apt install ffmpeg libsm6 libxext6  -y

# Step 6 - Install additional libraries for dlib and face_recognition
# For building image on local ubuntu system, uncomment following line
#RUN apt install cmake libboost-all-dev

# Step 7 - Copy and install project requirements
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Step 8 - Install Gmail APIs for sending email alerts
RUN pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Step 9 - Uncomment following line if we want to copy project contents to docker image
# COPY . .

# Step 10 - Give starting point of project which will be either Flask app or multicam server
# For running flask app, uncomment following
# CMD [ "python3", "-m" , "flask", "--app", "src/app", "run", "--host=0.0.0.0"]
# For running multicam server
# CMD ["python3", "src/dlib_face_recognition_multicam_server.py"]
# For just starting the container (i.e., we will have to manually execute the program from inside the container), uncomment next line
CMD ["sh"]
