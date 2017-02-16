from uuid import uuid4

class FileDTO:
    def __init__(self,
            id=None,
            filename=None,
            checksum=None,
            size=None,
            url=None,
            content=None):

        self.id = id or str(uuid4())
        self.filename = filename
        self.checksum = checksum
        self.url = url

        if content and isinstance(content, str):
            content = content.encode('utf-8')

        self.content = content
        self.size = size or (len(content) if content else 0)

    def as_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'checksum': self.checksum,
            'size': self.size,
            'url': self.url
        }

    def __eq__(self, f):
        return self.__check_equality(f)

    def __ne__(self, f):
        return not self.__check_equality(f)

    def __check_equality(self, f):
        if not isinstance(f, FileDTO):
            return False
        else:
            return self.checksum == f.checksum and self.filename == f.filename

