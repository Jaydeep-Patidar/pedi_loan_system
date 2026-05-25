from decimal import Decimal


def ensure_single_penalty_method(instance):
    """Ensure only one penalty method is enabled for a given model instance.

    This is used by both Payment and Loan payments.

    Expects instance to have boolean fields:
      - enable_late_fee_per_day
      - enable_fixed_penalty
      - enable_percentage_penalty

    And should leave exactly one enabled if enable_late_fee_per_day is true,
    else fixed, else percentage; otherwise do nothing.
    """

    # Normalize missing attributes gracefully
    late = bool(getattr(instance, "enable_late_fee_per_day", False))
    fixed = bool(getattr(instance, "enable_fixed_penalty", False))
    perc = bool(getattr(instance, "enable_percentage_penalty", False))

    enabled = [late, fixed, perc].count(True)
    if enabled <= 1:
        return instance

    # If multiple enabled, keep a deterministic order
    if late:
        setattr(instance, "enable_fixed_penalty", False)
        setattr(instance, "enable_percentage_penalty", False)
    elif fixed:
        setattr(instance, "enable_late_fee_per_day", False)
        setattr(instance, "enable_percentage_penalty", False)
    else:
        # percentage
        setattr(instance, "enable_late_fee_per_day", False)
        setattr(instance, "enable_fixed_penalty", False)

    return instance


# Backward compatible alias (the project references _ensure_single_penalty_method)
_ensure_single_penalty_method = ensure_single_penalty_method

