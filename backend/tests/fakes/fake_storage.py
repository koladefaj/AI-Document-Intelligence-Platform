class FakeStorage:
    async def upload(self, file_id, file_name, file_bytes, content_type):
        return f"fake://{file_id}"
    
    async def get_file_path(self, file_id):
        return f"/tmp/{file_id}"