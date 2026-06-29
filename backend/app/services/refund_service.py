from sqlalchemy.orm import Session
from ..models.payment import Payment
from ..models.booking import Booking
from ..models.shift_instance import ShiftInstance
from ..time_override import business_utcnow

def procesar_reembolso_clase_suelta(db: Session, booking: Booking, instance: ShiftInstance):
    """
    Calcula si corresponde devolver el 100% (paid) o el 50% (partial) 
    de una clase suelta y genera el asiento contable negativo en Payment.
    """
    precio_clase = instance.template.price if instance.template else None
    monto_a_devolver = float(booking.amount_paid) if booking.amount_paid is not None else 0.0
    
    if monto_a_devolver == 0.0 and precio_clase:
        factor = 0.5 if booking.payment_status == "partial" else 1.0
        monto_a_devolver = float(precio_clase) * factor

    if monto_a_devolver > 0:
        tipo_refund = "refund_partial" if booking.payment_status == "partial" else "refund_total"

        refund_entry = Payment(
            user_id=booking.user_id,
            amount=monto_a_devolver,
            status="completed",      
            type=tipo_refund,        
            date=business_utcnow()    
        )
        db.add(refund_entry)
        booking.payment_status = "refunded"