import pymysql
import boto3
import datetime
import math
import time

# connection = pymysql.connect(
#   host='localhost',
#   user='ece1779a1',
#   password='password123',
#   port=3306,
#   database='ece1779a1')

connection = pymysql.connect(
  host='ece1779a2-rds.coc6d8upfz6v.us-east-1.rds.amazonaws.com',
  user='ece1779a2',
  password='password123',
  port=3306,
  database='ece1779a2')

CPUUtilization_REQUEST = {
      "view": "timeSeries",
      "width": 600,
      "height": 395,
      "metrics": [
          ["AWS/EC2", "CPUUtilization", "InstanceId", "value of instance id", {"stat": "Sum"}]
      ],
      "period": 60,
      "start": "-PT0.5H",
      "stacked": False,
      "yAxis": {
          "left": {
              "min": 0.1,
          },
          "right": {
              "min": 0
          }
      }
    }


def get_auto_scaling_policy():
    cursor = connection.cursor()
    sql_get = "select * from worker_management where id=1"
    cursor.execute(sql_get)
    record = cursor.fetchone()
    if record is None:
        sql_add = "INSERT INTO worker_management (threshold_growing, threshold_shrinking, ratio_growing, ratio_shrinking) " \
                  "VALUES (80, 20, 2, 2)"
        cursor.execute(sql_add)
        connection.commit()
        record = (80, 20, 2.00, 2.00)
    return record


def get_current_cpu_util():
    client = boto3.client('elbv2')
    cloud_watch = boto3.client("cloudwatch")
    target_group = client.describe_target_health(
      TargetGroupArn="arn:aws:elasticloadbalancing:us-east-1:479498022568:targetgroup/ECE1779A2-TG/b7c975c015d56e4a")

    sum_cpu_avg = 0
    count = 0
    for target in target_group['TargetHealthDescriptions']:
        instance_id = target['Target']['Id']
        CPUUtilization_REQUEST["metrics"][0][3] = instance_id
        start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        dimensions = [
                       {
                         'Name': 'InstanceId',
                         'Value': instance_id
                       }
                     ]
        cpu_response = cloud_watch.get_metric_statistics(Namespace="AWS/EC2",
                                                         MetricName="CPUUtilization",
                                                         Dimensions=dimensions,
                                                         Statistics=['Average'],
                                                         StartTime=start_time,
                                                         EndTime=datetime.datetime.utcnow(),
                                                         Period=60)
        sum_cpu_avg = sum_cpu_avg + cpu_response['Datapoints'][0]['Average']
        count += 1

    return count, sum_cpu_avg/count


######################################
######################################
class manager:
    EC2 = boto3.client('ec2')
    ELB = boto3.client('elbv2')
    S3 = boto3.client('s3')

    def get_target_instance(self):
        target_group = self.ELB.describe_target_health(TargetGroupArn="arn:aws:elasticloadbalancing:us-east-1:479498022568:targetgroup/ECE1779A2-TG/b7c975c015d56e4a")
        instances_id = []
        if target_group['TargetHealthDescriptions']:
            for target in target_group['TargetHealthDescriptions']:
                if target['TargetHealth']['State'] != 'draining':
                    instances_id.append(target['Target']['Id'])
        return instances_id

    def create_new_instance(self):
        response = self.EC2.run_instances(
            ImageId="ami-0353607cefbd075a3",
            Monitoring={'Enabled': True},
            Placement={'AvailabilityZone': "us-east-1a"},
            InstanceType="t2.small",
            MinCount=1,
            MaxCount=1,
            UserData = '#!/bin/bash\n' \
                        'screen\n' \
                        '/home/ubuntu/Desktop/start.sh',
            KeyName='ece1779a2',
            SubnetId="subnet-d32d11fd",
            SecurityGroupIds=['sg-091c7fa2c83cd95cd'],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'a2'
                        },
                    ]
                 },
            ],
        )
        for instance in response['Instances']:
            print(instance['InstanceId'] + " created!")
        return response['Instances'][0]['InstanceId']

    def start_instance(self,instance_id):
        self.EC2.start_instances(InstanceIds=[instance_id])

    def stop_instance(self, instance_id):
        self.EC2.stop_instances(InstanceIds=[instance_id], Hibernate=False, Force=False)

    def get_stopped_instances(self):
        ec2_filter = [{'Name': 'tag:Name', 'Values': 'a2'},
                      {'Name': 'instance-state-name', 'Values': ['stopped']}]
        return self.EC2.describe_instances(Filters=ec2_filter)


    def register_target(self, instance_id):
        target_group="arn:aws:elasticloadbalancing:us-east-1:479498022568:targetgroup/ECE1779A2-TG/b7c975c015d56e4a"
        target = [{'Id': instance_id,
                   'Port': 5000}]
        self.ELB.register_targets(TargetGroupArn = target_group, Targets = target)


    def deregister_target(self, instance_id):
        target_group = "arn:aws:elasticloadbalancing:us-east-1:479498022568:targetgroup/ECE1779A2-TG/b7c975c015d56e4a"
        target = [{'Id': instance_id}]
        self.ELB.deregister_targets(TargetGroupArn=target_group,
                                    Targets=target)


    def terminate_instance(self, instance_id):
        self.EC2.terminate_instances(InstanceIds=[instance_id])


    def start_instances(self,instance_needs_to_start):
        target_instance_id = self.get_target_instance()
        expected_instance = len(target_instance_id) + instance_needs_to_start
        if len(target_instance_id) == 10:
            # set a flag that show we cannot grow anymore
            return False
        #We can only increase the total number of intance to 10
        if expected_instance > 10:
            instance_needs_to_start = 10 - len(target_instance_id)

        stopped_instances = self.get_stopped_instances()['Reservations']
        if stopped_instances:
            # if there exists stopped instances
            if len(stopped_instances) >= instance_needs_to_start:
                for i in range(instance_needs_to_start):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    self.start_instance(new_instance_id)
            else:
                for i in range(len(stopped_instances)):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    self.start_instance(new_instance_id)
                rest = instance_needs_to_start - len(stopped_instances)
                for i in range(rest):
                    new_instance_id = self.create_new_instance()
                    status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                    while len(status['InstanceStatuses']) < 1:
                        time.sleep(1)
                        status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                    while status['InstanceStatuses'][0]['InstanceState']['Name'] != 'running':
                        time.sleep(1)
                        status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                    self.register_target(new_instance_id)
        else:
            for i in range(instance_needs_to_start):
                new_instance_id = self.create_new_instance()
                status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                while len(status['InstanceStatuses']) < 1:
                    time.sleep(1)
                    status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                while status['InstanceStatuses'][0]['InstanceState']['Name'] != 'running':
                    time.sleep(1)
                    status = self.EC2.describe_instance_status(InstanceIds=[new_instance_id])
                self.register_target(new_instance_id)
        return True



    def stop_instances(self,instance_needs_to_stop):
        target_instance_id = self.get_target_instance()
        if len(target_instance_id) <= 1:
            return False
        if instance_needs_to_stop >= len(target_instance_id):
            for i in range(len(target_instance_id)-1):
                self.deregister_target(target_instance_id[0])
                self.stop_instance(target_instance_id[0])
        else:
            for i in range(len(instance_needs_to_stop)):
                self.deregister_target(target_instance_id[0])
                self.stop_instance(target_instance_id[0])
                time.sleep(1)
        return True

######################################
######################################

def get_monitor_info(instance_amount):
    cursor = connection.cursor()
    cursor.execute("select * from script_monitor where id=1")
    record = cursor.fetchone()
    print(record)
    if record is None:
        sql_add = "INSERT INTO script_monitor (current_instance_amount, retry_time) VALUES ({}, 5)".format(instance_amount)
        cursor.execute(sql_add)
        connection.commit()
        record = (instance_amount, 5)
    return record


def auto_scaling():
    policy = get_auto_scaling_policy()
    threshold_growing = policy[1]
    threshold_shrinking = policy[2]
    ratio_growing = policy[3]
    ratio_shrinking = policy[4]
    instance_amount, current_cpu_util = get_current_cpu_util()
    monitor = get_monitor_info(instance_amount)
    instance_amount_actual = monitor[1]
    retry_time_left = monitor[2]
    print(retry_time_left)
    if instance_amount_actual == instance_amount or retry_time_left == 0:
        if current_cpu_util > threshold_growing:
            instance_needs_to_start = math.floor(instance_amount * ratio_growing - instance_amount)
            if not manager.start_instances(instance_needs_to_start):
                ###这里写点啥中断程序？
                raise Exception('The worker pool is limited by 10. Cannot grow it up.')
            current_instance_amount = instance_amount + instance_needs_to_start
        elif current_cpu_util < threshold_shrinking:
            instance_needs_to_stop = math.floor(instance_amount/ratio_shrinking)
            if not manager.stop_instances(instance_needs_to_stop):
                raise Exception('The worker pool is limited by 1. Cannot shrink more.')
            current_instance_amount = instance_amount - instance_needs_to_stop
        else:
            current_instance_amount = instance_amount
        sql_update = "UPDATE script_monitor SET current_instance_amount={}, retry_time=5 WHERE id=1".format(current_instance_amount)

    else:
        sql_update = "UPDATE script_monitor SET retry_time={} WHERE id=1".format(retry_time_left-1)
    cursor = connection.cursor()
    cursor.execute(sql_update)
    connection.commit()


if __name__ == "__main__":
    auto_scaling()





