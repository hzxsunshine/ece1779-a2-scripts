# Initialize the worker pool size to 1.
# Will be run only at starting manager app
import boto3
import time


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
        ec2_filter = [{'Name': 'tag:Name', 'Values': ['a2']},
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

        ###
        TempIDs = []
        ###

        if len(target_instance_id) == 10:
            # set a flag that show we cannot grow anymore
            return 0
        #We can only increase the total number of intance to 10
        if expected_instance > 10:
            instance_needs_to_start = 10 - len(target_instance_id)

        stopped_instances = self.get_stopped_instances()['Reservations']
        if stopped_instances:
            # if there exists stopped instances
            if len(stopped_instances) >= instance_needs_to_start:
                for i in range(instance_needs_to_start):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    TempIDs.append(new_instance_id)
                    self.start_instance(new_instance_id)
                status = self.EC2.describe_instance_status(InstanceIds=TempIDs)
                while len(status['InstanceStatuses']) < len(TempIDs):
                    time.sleep(1)
                    status = self.EC2.describe_instance_status(InstanceIds=TempIDs)
                for i in range(len(TempIDs)):
                    while status['InstanceStatuses'][i]['InstanceState']['Name'] != 'running':
                        time.sleep(1)
                        status = self.EC2.describe_instance_status(InstanceIds=TempIDs)
                for id in TempIDs:
                    self.register_target(id)
            else:
                for i in range(len(stopped_instances)):
                    new_instance_id = stopped_instances[i]['Instances'][0]['InstanceId']
                    TempIDs.append(new_instance_id)
                    self.start_instance(new_instance_id)

                rest = instance_needs_to_start - len(stopped_instances)

                for i in range(rest):
                    new_instance_id = self.create_new_instance()
                    TempIDs.append(new_instance_id)

                status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

                while len(status['InstanceStatuses']) < len(TempIDs):
                    time.sleep(1)
                    status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

                for i in range(len(TempIDs)):
                    while status['InstanceStatuses'][i]['InstanceState']['Name'] != 'running':
                        time.sleep(1)
                        status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

                for id in TempIDs:
                    self.register_target(id)
        else:
            for i in range(instance_needs_to_start):
                new_instance_id = self.create_new_instance()
                TempIDs.append(new_instance_id)
            status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

            while len(status['InstanceStatuses']) < len(TempIDs):
                time.sleep(1)
                status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

            for i in range(len(TempIDs)):
                while status['InstanceStatuses'][i]['InstanceState']['Name'] != 'running':
                    time.sleep(1)
                    status = self.EC2.describe_instance_status(InstanceIds=TempIDs)

            for id in TempIDs:
                self.register_target(id)
        return instance_needs_to_start



    def stop_instances(self, instance_needs_to_stop):
        target_instance_id = self.get_target_instance()
        if len(target_instance_id) < 1:
            return 0
        if instance_needs_to_stop >= len(target_instance_id):
            for i in range(len(target_instance_id)-1):
                self.deregister_target(target_instance_id[i])
                self.stop_instance(target_instance_id[i])
            return len(target_instance_id)-1
        return instance_needs_to_stop



def Init():
    m = manager()
    InstancesId = m.get_target_instance()
    if len(InstancesId) != 0:
        if len(InstancesId) > 1:
            m.stop_instances(10)
        if len(InstancesId) == 1:
            return
    else:
        m.start_instances(1)
        return
    return

if __name__ == "__main__":
    #Check
    Init()