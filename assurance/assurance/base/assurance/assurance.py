import logging

from pydantic import ValidationError


class AssuranceException(Exception):
    pass

class Assurance:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def pydantic_error(self, e: ValidationError) -> dict:
        reasons = []
        for error in e.errors():
            reasons.append({
                'loc': error['loc'],
                'msg': error['msg'],
                'type': error['type']
            })
        return {'reasons': reasons, 'input': e.errors()[0]['input']}
