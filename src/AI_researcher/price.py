import numbers


class InputFormats:
    KTOKEN = "1k token"
    MIN = "minute"


class Price:
    def __init__(self, inputPrice, outputPrice):
        self.totalPrice = inputPrice+outputPrice
        self.inputPrice = inputPrice
        self.outputPrice = outputPrice

    @staticmethod
    def readablePrice(price):
        return f"${round(price, 2)}"

    def __str__(self):
        return f"Total price: {self.readablePrice(self.totalPrice)} (input price: {self.readablePrice(self.inputPrice)}, output price: {self.readablePrice(self.outputPrice)})"


def textToToken(text):
    return lenToToken(len(text))


def lenToToken(len):
    return len/4


class gpt_4_1106_preview:
    input_price = 0.01
    output_price = 0.06
    output_format = InputFormats.KTOKEN

    def calcPrice(self, inputText, outputText, inputLength=None, outputLength=None):
        """Calculates the price of a run"""
        if not inputLength:
            inputPrice = textToToken(inputText)*self.input_price/1000
        else:
            inputPrice = lenToToken(inputLength)*self.input_price/1000

        if not outputLength:
            outputPrice = textToToken(outputText)*self.output_price/1000
        else:
            outputPrice = lenToToken(outputLength)*self.output_price/1000

        return Price(inputPrice, outputPrice)

class whisper:
    input_price = 0.006
    output_format = InputFormats.MIN

    def calcPrice(self, input):
        if not isinstance(input, numbers.Number):
            pass

        return Price(input*self.input_price, 0)