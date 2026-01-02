from django.test import TestCase

from chats.apps.core.integrations.aws.s3.helpers import is_file_in_the_same_bucket


class TestIsFileInTheSameBucket(TestCase):
    def setUp(self):
        self.bucket_name = "test-bucket"

    def test_is_file_in_the_same_bucket_when_url_follow_s3_protocol_scheme(self):
        url = f"s3://{self.bucket_name}/test/file.txt"
        self.assertTrue(is_file_in_the_same_bucket(url, self.bucket_name))

    def test_is_file_in_the_same_bucket_when_url_follow_virtual_hosted_style(self):
        url = f"https://{self.bucket_name}.s3.amazonaws.com/test/file.txt"
        self.assertTrue(is_file_in_the_same_bucket(url, self.bucket_name))

    def test_is_file_in_the_same_bucket_when_url_follow_path_style(self):
        url = f"https://s3.amazonaws.com/{self.bucket_name}/test/file.txt"
        self.assertTrue(is_file_in_the_same_bucket(url, self.bucket_name))

    def test_is_file_in_the_same_bucket_when_url_follow_regional_style(self):
        url = f"https://s3.us-east-1.amazonaws.com/{self.bucket_name}/test/file.txt"
        self.assertTrue(is_file_in_the_same_bucket(url, self.bucket_name))

    def test_is_file_in_the_same_bucket_when_url_follow_dualstack_style(self):
        url = f"https://{self.bucket_name}.s3.dualstack.amazonaws.com/test/file.txt"
        self.assertTrue(is_file_in_the_same_bucket(url, self.bucket_name))

    def test_is_file_in_the_same_bucket_when_url_is_not_in_the_same_bucket(self):
        url = f"https://{self.bucket_name}.s3.amazonaws.com/test/file.txt"
        self.assertFalse(is_file_in_the_same_bucket(url, "other-bucket"))
