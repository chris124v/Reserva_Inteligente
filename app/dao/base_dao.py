
from abc import ABC, abstractmethod

#Define que metodos debe tener cualquier DAO, pero no implementa nada eso lo hacen los hijos
# La clase hija ya tiene esta base dao y ella define el como, osea si lo usa sql server o mongo etc
class BaseDAO(ABC):  # ABC = Abstract Base Class
    @abstractmethod
    def get_by_id(self, id):
        pass