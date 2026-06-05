
class BaseLLMAgent(object):
    def __init__(self, config):
        self.config = config
        self.load_config(self.config)
        


    def load_config(self, config):
        self.model_name = config.model_name
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.top_p = config.top_p
        self.model_card = config.model_card
        self.tokenizer_card = config.tokenizer_card


    def load_model(self):
        raise NotImplementedError("Subclasses must implement this method")

    def load_tokenizer(self):
        raise NotImplementedError("Subclasses must implement this method")

    def generate_response(self, prompt):
        raise NotImplementedError("Subclasses must implement this method")

        
    def beam_search(self, prompt, num_beams=5):
        raise NotImplementedError("Subclasses must implement this method")


    def greedy_search(self, prompt):
        raise NotImplementedError("Subclasses must implement this method")


    def nucleus_sampling(self, prompt, top_p=0.9):
        raise NotImplementedError("Subclasses must implement this method")
