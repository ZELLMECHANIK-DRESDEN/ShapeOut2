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
- Shape-Out 2 does not provide a linear mixed effects models
  (LMM) analysis. LMM analysis in Shape-Out 1 is done using
  `R/lme4 <https://cran.r-project.org/web/packages/lme4/>`_ and thus
  requires a full R distribution shipped with Shape-Out 1. This
  blows up the installation size and makes it more difficult to deploy.
  Furthermore (and we are not saying that LMM Analysis is "bad") we are
  also looking into other methods for determining statistical significance
  which might be more intuitive to understand.



Terminology
===========
Shape-Out 2 introduces several terms in the user interface that also play
a role in data analysis and are consequently used in the entire code base.

block matrix
    The :ref:`sec_block_matrix` is a visualization of the analysis
    pipeline. It is divided into data matrix (filters) and plot matrix (plots).

dataslot or slot
    A slot holds all information about a measurement: the path to the
    .rtdc file, fluorescence labels, display color, etc. (see the
    *Dataset* tab in the :ref:`sec_analysis_view`).

filter
    A filter is a set of filtering options (box filter, polygon filter,
    downsampling, etc.) that can be applied to a slot (see the
    *Filter* tab in the :ref:`sec_analysis_view`). Filters can be exported
    and imported again in Shape-Out 2 (.sof file format).

filter ray
    A filter ray is a list of filters that can be applied to a slot.
    In Shape-Out 2, each row in the :ref:`sec_block_matrix` contains
    one filter ray.

pipeline
    A pipeline consists of all filters, slots, plots, and the filter rays
    (the filter selection) applied to each slot. A Shape-Out 2 session file
    (.so2) stores all information necessary to rebuild a pipeline.

plot
    A plot is a user-defined visualization of a slot/filter ray combination.



Basic usage
===========
.. image:: scrots/ui_main.png
    :target: _images/ui_main.png
    :align: right
    :scale: 20%

The user interface is split into several parts: the menu bar and the tool
bar at the top, the Block Matrix on the left, and the Workspace on the right
(example data taken from :cite:`NawUrb2019`, :cite:`NawUrb2019data`).


Menu bar and tool bar
---------------------
The menu bar is used for session management (File menu)
and makes additional functionalities available, such as batch
processing, data statistics, data export, plot export, or filter import/export.
The tool bar contains shortcuts for adding new datasets,
filters, or plots (left part) and allows to hide/show the
:ref:`sec_block_matrix` as well as the :ref:`sec_quick_view` and
:ref:`sec_analysis_view` windows (right part).


.. _sec_block_matrix:

Block Matrix
------------
.. image:: scrots/ui_block_matrix.png
    :target: _images/ui_block_matrix.png
    :align: right
    :scale: 65%

The Block Matrix gives an overview of the current analysis
pipeline. Each row represents a dataset (purple). The columns represent
either filters (yellow) or plots (blue) of your pipeline.
You can change the order of datasets via the *Edit|Change dataset order*
menu bar entry.

You can perform dataset operations in the purple rectangular area
at the beginning of each row: To modify a dataset, click on the *edit*
button. You can duplicate, insert anew (unmodified), or remove datasets
using the dropdown menu. You can also exclude a dataset from an analysis
via the check box.

Filters can also be modified, copied, removed and disabled.
By default, all filters are disabled when they are created. To apply a filter
to a dataset, click on the corresponding matrix element. The element changes
its color from gray (incactive) to green (active). In Shape-Out, all
filters that are applied to a dataset are called a **filter ray**.
In the above example, the filter ray only consists of a single filter for each
dataset. Filter rays may be different for each dataset. 

By holding down the *Shift* key while clicking on a matrix element, you
can activate the :ref:`Quick View <sec_quick_view>` for the specific
dataset (with filters applied up until the selected column). The block matrix
element is then colored pink.

To add a plot, click on the *New Plot* button in the tool bar. This adds
a plot column with a blue header to the Block Matrix and creates an empty
plot window. You can add datasets to your plot by clicking on the
corresponding matrix elements. In the above example, both datasets are
being used in all three plots. 

The modification of datasets, filters, and plots is discussed below.


Workspace
---------
The Workspace is designed as an infinite scrollable area and contains all
plot windows as well as the :ref:`sec_quick_view` and Analysis View windows.


.. _sec_analysis_view:

Analysis View
-------------
The analysis view is separated into four tabs (see screenshots below).

- The **Meta** tab displays all metadata of the selected dataset that
  are stored in the original .rtdc file.
- The **Dataset** tab allows to
  specify additional metadata, such as unique colors used for plotting and
  additional metadata for computing the Young's modulus or correcting
  for fluorescence cross-talk. It also allows to specify fluorescence
  channel labels that will then be used for labeling the axes of plots.
- The **Filter** tab is used to modify the filters of the pipeline.
  New box filters can be added by selecting *Choose box filters...*.
  Polygon filters are created in the :ref:`sec_quick_view` window.
- The **Plot** tab allows to specify all plotting parameters. Please
  take special note of the *Division* option in the *Layout* section (defines
  the arrangement of the subplots) and the *Marker hue* option in the
  *Scatter plot* section (allows you the specify whether the scatter
  data points are colored according to a kernel density estimate (KDE),
  another feature dimension, or the dataset color specified in the
  *Dataset* tab). In this example, contour plots are not used.

.. image:: scrots/ui_ana_meta.png
    :target: _images/ui_ana_meta.png
    :scale: 65%

.. image:: scrots/ui_ana_slot.png
    :target: _images/ui_ana_slot.png
    :scale: 65%

.. image:: scrots/ui_ana_filter.png
    :target: _images/ui_ana_filter.png
    :scale: 65%

.. image:: scrots/ui_ana_plot.png
    :target: _images/ui_ana_plot.png
    :scale: 65%


.. _sec_quick_view:

Quick View
----------
The Quick View is meant for dataset exploration. It consists of a scatter plot
on the left (left click for panning and right-click for zooming) and a set of
tool panels that are accessible via the corresponding tool buttons on the right.


Use the **Plot** panel to define all plot parameters. It also displays
common statistics of the two features plotted.

.. image:: scrots/ui_qv_settings.png
    :target: _images/ui_qv_settings.png
    :scale: 65%

The **Event** panel displays all parameters of an individual event. You can
select single events by clicking in the scatter plot or by scrolling through
the *Index* spin control. If available, the event image is shown alongside the
fluorescence trace of the event. All features of the event are listed in a
separate tab.

.. image:: scrots/ui_qv_event.png
    :target: _images/ui_qv_event.png
    :scale: 65%

The **Polygon Filter** panel allows you to create and modify polygon filters.
When the panel is active you can move the mouse pointer across the scatter
plot and the image of the event closest to the mouse pointer is displayed.

.. image:: scrots/ui_qv_poly.png
    :target: _images/ui_qv_poly.png
    :scale: 65%
