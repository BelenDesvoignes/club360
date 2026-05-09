from backend.app.database import _SessionLocal
from backend.app.models.user import User
from backend.app.models.shift_instance import ShiftInstance
from backend.app.services.booking_service import create_booking

if __name__ == '__main__':
    db = _SessionLocal()
    user = db.query(User).first()
    inst = db.query(ShiftInstance).first()
    print('user_id=', user.id_user)
    print('instance_id=', inst.id)
    try:
        b = create_booking(db, user.id_user, inst.id)
        print('booking ok id=', b.id, 'status=', b.status)
    except Exception as e:
        print('exception:', repr(e))
