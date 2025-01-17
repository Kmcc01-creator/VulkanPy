class World:
    def __init__(self):
        self.entities = []
        self.components = {}
        self.systems = []

    def create_entity(self):
        entity = len(self.entities)
        self.entities.append(entity)
        return entity

    def add_component(self, entity, component):
        component_type = type(component)
        if component_type not in self.components:
            self.components[component_type] = {}
        self.components[component_type][entity] = component

    def get_component(self, entity, component_type):
        return self.components.get(component_type, {}).get(entity)

    def add_system(self, system):
        self.systems.append(system)

    def update(self):
        for system in self.systems:
            system.update(self)
