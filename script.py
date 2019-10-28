import pymysql
import boto3
import datetime
import math

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
      TargetGroupArn="arn:aws:elasticloadbalancing:us-east-1:935290738939:targetgroup/ECE1779A2-TG/91f7c395a87d8fac")

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


def start_instance(instance_needs_to_start):
    return


def stop_instance(instance_needs_to_stop):
    return


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
            start_instance(instance_needs_to_start)
            current_instance_amount = instance_amount + instance_needs_to_start
        elif current_cpu_util < threshold_shrinking:
            instance_needs_to_stop = math.ceil(instance_amount/ratio_shrinking)
            stop_instance(instance_needs_to_stop)
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





