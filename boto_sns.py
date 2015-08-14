import boto
import boto.exception
import boto.sns
import pprint
import re
import settings


def send_push(device_id, body):
    region = [r for r in boto.sns.regions() if r.name == u'eu-west-1'][0]

    sns = boto.sns.SNSConnection(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region=region,
    )   
    
    try:
        endpoint_response = sns.create_platform_endpoint(
            platform_application_arn=settings.PLATFORM_APPLICATION_ARN,
            token=device_id,
        )   
        endpoint_arn = endpoint_response['CreatePlatformEndpointResponse']['CreatePlatformEndpointResult']['EndpointArn']
    except boto.exception.BotoServerError as err:
        # Yes, this is actually the official way:
        # http://stackoverflow.com/questions/22227262/aws-boto-sns-get-endpoint-arn-by-device-token
        result_re = re.compile(r'Endpoint(.*)already', re.IGNORECASE)
        result = result_re.search(err.message)
        if result:
            endpoint_arn = result.group(0).replace('Endpoint ', '').replace(' already', '')
        else:
            raise
            
    print("ARN:", endpoint_arn)

    publish_result = sns.publish(
        target_arn=endpoint_arn,
        message=body,
    )
    print("PUBLISH")
    pprint.pprint(publish_result)