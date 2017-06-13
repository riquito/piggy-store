class FileDTO:
    def __init__(self,
                 object_name=None,
                 checksum=None,
                 size=None,
                 url=None,
                 content=None,
                 path_separator='/'):

        self.object_name = object_name
        self.checksum = checksum
        self.url = url
        self.path_separator = path_separator

        if content and isinstance(content, str):
            content = content.encode('utf-8')

        self.content = content
        self.size = size or (len(content) if content else 0)

    def as_dict(self):
        return {
            'filename': self.get_filename(),
            'checksum': self.checksum,
            'size': self.size,
            'url': self.url
        }

    def clone(self, **kwargs):
        raw_file = dict(
            object_name=self.object_name,
            checksum=self.checksum,
            size=self.size,
            url=self.url,
            content=self.content,
            path_separator=self.path_separator
        )

        for k, v in kwargs.items():
            raw_file[k] = v

        return FileDTO(**raw_file)

    def get_filename(self):
        return self.object_name.rsplit(self.path_separator)[-1] if self.object_name else ''

    def __repr__(self):
        return '<FileDTO filename:{} checksum:{}>'.format(self.get_filename(), self.checksum)
