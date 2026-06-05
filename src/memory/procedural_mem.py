

class ProceduralMemory(object):
    def __init__(self, model_config):
        self.model_config = model_config
        self.memory = {}

    def store(self, key, value):
        self.memory[key] = value


    def retrieve(self, key):
        return self.memory.get(key, None)


    def delete(self, key):
        if key in self.memory:
            del self.memory[key]

            
    def clear(self):
        self.memory.clear()