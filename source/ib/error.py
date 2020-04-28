class IBError(Exception):
    """
    Error object to handle the error retruns from IB
    """

    def __init__(self, id: int, errorCode: int, errorString: str):
        self.id = id
        self.errorCode = errorCode
        self.errorString = errorString

        super().__init__(errorString)

    def __str__(self):
        # override method
        error_msg = "IB error id %d errorcode %d string %s" \
            % (self.id, self.errorCode, self.errorString)

        return error_msg
