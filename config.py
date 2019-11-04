class Config(object):
    DEBUG = True
    LOGGING_FILE_PATH = "/ece1779-manager-app.log"
    TESTING = False

    SECRET_KEY = "fe8e5c349e8eb13bf65bdc261229d43d"

    TARGET_GROUP_ARN = "arn:aws:elasticloadbalancing:us-east-1:479498022568:targetgroup/ECE1779A2-TG/b7c975c015d56e4a"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = "mysql://root:hzx960209@localhost/a2"

    #SQLALCHEMY_DATABASE_URI = "mysql://ece1779a2:password123@ece1779a2-rds.coc6d8upfz6v.us-east-1.rds.amazonaws.com/ece1779a2"

    AMI_ID = 'ami-0f7118067ffa41e5f'
    INSTANCE_TYPE = 't2.small'
    KEYNAME = 'ece1779a2'
    SG = ['sg-091c7fa2c83cd95cd']
    ZONE = 'us-east-1a'
    EC2NAME = 'a2'
    SUBNETID = 'subnet-d32d11fd'
    USERDATA = '#!/bin/bash\n' \
               'screen\n' \
               '/home/ubuntu/Desktop/start.sh'

    MANAGER_NAME = 'ECE1779A2-manager-app'
    S3_BUCKET = "2019fall-ece1779a2"
