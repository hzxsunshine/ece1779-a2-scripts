import pymysql
import boto3
import datetime
import math
import config

# connection = pymysql.connect(
#   host='localhost',
#   user='ece1779a1',
#   password='password123',
#   port=3306,
#   database='ece1779a1')

connection = pymysql.connect(
  host='ece1779a2.csmeodxl9uyw.us-east-1.rds.amazonaws.com',
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
      TargetGroupArn=config.Config().TARGET_GROUP_ARN)

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

    def create_new_instance(self,min,max):
        Config = config.Config()
        response = self.EC2.run_instances(
            ImageId=Config.AMI_ID,
            Monitoring={'Enabled': True},
            Placement={'AvailabilityZone': Config.ZONE},
            InstanceType=Config.INSTANCE_TYPE,
            MinCount=min,
            MaxCount=max,
            UserData = Config.USERDATA,
            KeyName=Config.KEYNAME,
            SubnetId=Config.SUBNETID,
            SecurityGroupIds=Config.SG,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': Config.EC2NAME
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

    def get_running_instances(self):
        ec2_filter = [{'Name': 'tag:Name', 'Values': 'a2'},
                      {'Name': 'instance-state-name', 'Values': ['running']}]
        return self.EC2.describe_instances(Filters=ec2_filter)


    def start_instance(self,instance_needs_to_start):
        stopped_instances = self.get_stopped_instances()['Reservations']
        if stopped_instances:
            if len(stopped_instances) >= instance_needs_to_start:
                for i in range(instance_needs_to_start):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    self.start_instance(new_instance_id)
            else:
                for i in range(len(stopped_instances)):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    self.start_instance(new_instance_id)
                rest = instance_needs_to_start - len(stopped_instances)
                self.create_new_instance(rest,rest)
        else:
            self.create_new_instance(instance_needs_to_start,instance_needs_to_start)
        return



    def stop_instance(self,instance_needs_to_stop):
        ids = self.get_running_instances()['InstanceId'][0:(instance_needs_to_stop-1)]
        self.EC2.instances.filter(InstanceIds=ids).stop()
        return

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
            instance_needs_to_start = math.ceil(instance_amount * ratio_growing - instance_amount)
            manager.start_instance(instance_needs_to_start)
            current_instance_amount = instance_amount + instance_needs_to_start
        elif current_cpu_util < threshold_shrinking:
            instance_needs_to_stop = math.ceil(instance_amount/ratio_shrinking)
            manager.stop_instance(instance_needs_to_stop)
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





