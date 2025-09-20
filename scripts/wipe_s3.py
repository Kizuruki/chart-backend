import yaml
import aioboto3
import asyncio

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)


async def delete_s3_objects():
    s3_config = config["s3"]
    bucket_name = s3_config["bucket-name"]
    access_key_id = s3_config["access-key-id"]
    secret_access_key = s3_config["secret-access-key"]
    endpoint_url = s3_config["endpoint"]

    async with aioboto3.Session().client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        endpoint_url=endpoint_url,
    ) as s3_client:
        response = await s3_client.list_objects_v2(Bucket=bucket_name)

        if "Contents" in response:
            delete_objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
            delete_response = await s3_client.delete_objects(
                Bucket=bucket_name, Delete={"Objects": delete_objects}
            )
            print(f"Deleted {len(delete_objects)} objects.")
        else:
            print("No objects found in the bucket.")


asyncio.run(delete_s3_objects())
