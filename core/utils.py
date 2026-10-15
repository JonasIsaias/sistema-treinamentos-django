from datetime import timedelta

def add_workdays(start_date, workdays):
    """
    Soma 'workdays' dias úteis a partir de 'start_date'.
    (0=segunda, 4=sexta)
    """
    current_date = start_date
    added_days = 0
    while added_days < workdays:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            added_days += 1
    return current_date