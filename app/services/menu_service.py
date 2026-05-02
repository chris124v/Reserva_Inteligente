from app.models.user import RoleEnum
from app.schemas.menu import MenuCreate


def validate_menu_admin(user_dao, restaurant_dao, admin_id: int, restaurante_id: int):
    """
    Valida que el usuario sea admin y dueño del restaurante.
    Retorna el restaurante si es válido.
    """
    from fastapi import HTTPException

    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden modificar menús")

    restaurante = restaurant_dao.get_by_id(restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != admin_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar menús en este restaurante")

    return restaurante