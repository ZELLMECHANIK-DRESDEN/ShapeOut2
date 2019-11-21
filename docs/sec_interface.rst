==============
User Interface
==============


Differences to Shape-Out 1
==========================
Shape-Out 2 is a complete rewrite of the user interface from scratch.
The overall user experience is much better compared to Shape-Out 1.
The main reasons for the development of Shape-Out 2 were:

- The graphical user interface (GUI) of Shape-Out 1 was designed to
  be flexible with regard to new configuration parameters. While this
  played well for the beginning of RT-DC development, the GUI now appears
  not very thought-out for a mature measuring technique. The workflow
  of Shape-Out 2 has been designed to meet most of its users needs.
- Shape-Out 1 is condemned to Python 2 (which reached its end of life
  January 1st 2020), because it relies on the combination of chaco
  (for plotting) with wxPython 3 (for the GUI). Chaco is now focusing
  on PyQt and thus does not support the new wxPython 4. However,
  wxPython 3 does not support Python 3, so we are stuck with Python 2.
- For Shape-Out 1, there appeared a `weird issue
  <https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut/issues/243>`_
  which is probably related to the old wxPython library and some other
  software installed on some Windows systems.

Both versions of Shape-Out rely on :ref:`dclab <dclab:index>` which
provides the core functionalities for RT-DC data analysis. There are,
however, a few breaking changes that might prevent you from moving
your data analysis from Shape-Out 1 to Shape-Out 2:

- Shape-Out 2 does not anymore support the .tdms file format. If you
  would like to use .tdms data in Shape-Out 2, you have to convert those
  data to the .rtdc file format first. You can do just that with
  `DCKit <https://github.com/ZELLMECHANIK-DRESDEN/DCKit/releases/latest>`_,
  which provides a convenient GUI for several other RT-DC data
  management tasks as well. The .rtdc file format is faster, occupies less
  space on disk, and consists of only one file per measurement
  (no more para.ini, etc.).
- Shape-Out 1 sessions cannot be opened in Shape-Out 2. This is mostly
  caused by the different approach to data analysis. In principle, it
  could be possible to convert sessions (including the corresponding
  .tdms files), but the effort in doing so would probably exceed the
  effort required to just rebuild a clean analysis session in Shape-Out 2.
- Shape-Out 2 currently does not provide a linear mixed effects models
  (LMM) analysis. The reason behind that is quite pragmatic: LMM analysis
  in Shape-Out 1 is done using
  `R/lme4 <https://cran.r-project.org/web/packages/lme4/>`_ and thus
  requires a full R distribution shipped with Shape-Out 1. While this
  blows up the download and installation size, it is also not clear
  whether it would work just like that on macOS. However, if many users
  need this feature, then we can think of a workaround.


Basic usage
===========
TODO
