from dclab.rtdc_dataset import ancillaries

#: integer-valued features
INTEGER_FEATURES = [
    "fl1_max",
    "fl1_npeaks",
    "fl2_max",
    "fl2_npeaks",
    "fl3_max",
    "fl3_npeaks",
    "frame",
    "index",
    "ml_class",
    "nevents",
]

#: ancillary features that are easily computed
QUICK_FEATURES = ancillaries.FEATURES_RAPID
