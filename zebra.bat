Net use LPT1: /Delete
Net use LPT1: \\%ComputerName%\printer
Copy %1 LPT1
Net use LPT1: /Delete
PAUSE

Net use LPT2: \\%ComputerName%\LABELPRINTER
Copy %1 LPT2
Net use LPT2: /Delete
PAUSE