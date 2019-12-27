import sqlite3
import serial
import picamera     # Importing the library for camera module
import datetime as dt
import time
import os
import sys
import RPi.GPIO as GPIO
from digitalio import DigitalInOut, Direction
import adafruit_fingerprint
import signal

def takePhoto():
    from time import sleep
    from google.cloud import storage
    from firebase import firebase
    camera = picamera.PiCamera()    # Setting up the camera
    fname = (time.strftime("%Y-%m-%d %H:%M:%S"))
    lokasi = ("/home/pi/Desktop/ " + fname + ".jpg")
    uploadFirebase = camera.capture(lokasi) # Capturing the image
    camera.resolution = (1024, 720)
    # camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sleep(1)
    camera.stop_preview()
    print('Done')
    camera.close()
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=('/home/pi/Desktop/holdor-v001.json')
    firebase = firebase.FirebaseApplication('https://holdor-v001.firebaseio.com/')

    # Enable Storage
    client = storage.Client()

    # Reference an existing bucket.
    bucket = client.get_bucket('holdor-v001.appspot.com')

    # Upload a local file to a new file to be created in your bucket.
    imageBlob = bucket.blob(lokasi)
    imageBlob.upload_from_filename(lokasi)
    link_image = imageBlob.public_url
    print(link_image)
        
    data =  { 'id_ektp': ektp_in,  
              'id_finger': finger_in,  
              'accessor': nama,
              'access_time' : access_time,
              'access_date' : access_date,
              'status_valid' : status_valid,
              'image_link': link_image
              }  
    result = firebase.post('/holdor/',data)
    print(result)
    #sleep(5)
    
    

# Button pin
P_BUTTON = 17 # adapt to your wiring
O_BUTTON = 27
LED1 = 22
LED2 = 24
Flag = True

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(P_BUTTON, GPIO.IN)
    GPIO.setup(O_BUTTON, GPIO.IN)
    GPIO.setup(23,GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED1,GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED2,GPIO.OUT, initial=GPIO.LOW)
setup()

def unlockDor():
    #print("Solenoid Unlock")
    GPIO.output(23,GPIO.HIGH)

def lockDor():
    #print("Solenoid Lock")
    GPIO.output(23,GPIO.LOW)
    
conn = sqlite3.connect('/home/pi/Desktop/holdor.db')
c = conn.cursor()

uart = serial.Serial("/dev/ttyUSB1", baudrate=57600, timeout=1)
# uart = busio.UART(board.TX, board.RX, baudrate=57600)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
    

def get_fingerprint():
    """Get a finger print image, template it, and see if it matches!"""
    print("Waiting for fingerprint...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    #print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        return False
    #print("Searching...")
    if finger.finger_fast_search() != adafruit_fingerprint.OK:
        return False
    print(finger.finger_id)
    return True
# pylint: disable=too-many-branches
def get_fingerprint_detail():
    """Get a finger print image, template it, and see if it matches!
    This time, print out each error instead of just returning on failure"""
    print("Getting image...", end="", flush=True)
    i = finger.get_image()
    if i == adafruit_fingerprint.OK:
        print("Image taken")
    else:
        if i == adafruit_fingerprint.NOFINGER:
            print("No finger detected")
        elif i == adafruit_fingerprint.IMAGEFAIL:
            print("Imaging error")
        else:
            print("Other error")
        return False

    print("Templating...", end="", flush=True)
    i = finger.image_2_tz(1)
    if i == adafruit_fingerprint.OK:
        print("Templated")
    else:
        if i == adafruit_fingerprint.IMAGEMESS:
            print("Image too messy")
        elif i == adafruit_fingerprint.FEATUREFAIL:
            print("Could not identify features")
        elif i == adafruit_fingerprint.INVALIDIMAGE:
            print("Image invalid")
        else:
            print("Other error")
        return False

    print("Searching...", end="", flush=True)
    i = finger.finger_fast_search()
    # pylint: disable=no-else-return
    # This block needs to be refactored when it can be tested.
    if i == adafruit_fingerprint.OK:
        print("Found fingerprint!")
        return True
    else:
        if i == adafruit_fingerprint.NOTFOUND:
            print("No match found")
        else:
            print("Other error")
        return False


while True:
    print("Tap RFID Tag")
    id_tag = ""
    ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
    ambil_data = ser.readline()
    datastring = str(ambil_data)
    if ambil_data: 
        id_rf = ""
        buang1 = ""
        id_rf, buang1 = datastring.split("-")
        buang3 = ""
        buang3, id_tag = id_rf.split("'")
        print(id_tag)
        GPIO.output(LED2, GPIO.HIGH)
    
        #get_fingerprint()
        if finger.read_templates() != adafruit_fingerprint.OK:
            raise RuntimeError('Failed to read templates')
            
        ektp_in = id_tag
        finger_in = ""
        nama = ""
        valid = ""
        status_valid = ""
        access_time = time.strftime("%H:%M")
        access_date = time.strftime("%Y-%m-%d")
            
            
        if get_fingerprint():
            print("Detected #", finger.finger_id, "with confidence", finger.confidence)
            finger_in = finger.finger_id
        else:
            print("Finger not found")
            finger_in = "None"
            
        c.execute("SELECT username FROM dataUser WHERE id_ektp = ? AND id_finger = ?",
                    [ektp_in, finger_in])
        baca = c.fetchone()

        c.execute("SELECT * FROM dataUser WHERE id_ektp = ? AND id_finger = ?",
                    [ektp_in, finger_in])
        if c.fetchone() is not None:
            print("Buka")
            nama = baca[0]
            valid = "true"
                
        else:
            print("Tutup")
            nama = "Unidentified"
            valid = "valse"
                
            
        if valid == "true":
            print(nama)
            print("Buka")
            status_valid = "Izin akses diterima"
            unlockDor()
            takePhoto()
            GPIO.output(LED1, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(LED2, GPIO.LOW)
            GPIO.output(LED1, GPIO.LOW)
            
        elif valid == "valse":
            status_valid = "Izin akses ditolak"
            lockDor()
            takePhoto()
            GPIO.output(LED1, GPIO.LOW)
            GPIO.output(LED2, GPIO.LOW)
        
        
    if (GPIO.input(P_BUTTON) == GPIO.LOW and Flag == True):
        print("Tutup")
        Flag = False
        lockDor()
        
    elif (GPIO.input(P_BUTTON) == GPIO.HIGH and Flag == False):
        print("OFF")
        Flag = True
        GPIO.output(LED1, GPIO.LOW)
        GPIO.output(LED2, GPIO.LOW)
    
    else :
        Flag = True
            
    if (GPIO.input(O_BUTTON) == GPIO.LOW and Flag == True):
        print("Buka dari dalam")
        Flag = False
        unlockDor()