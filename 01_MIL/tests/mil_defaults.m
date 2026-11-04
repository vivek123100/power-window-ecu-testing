% MIL_DEFAULTS  Default inputs for running PowerWindow_MIL by hand.
% Run this once before pressing "Run" in Simulink.
% Inputs are [time value]: [0 0; 1 1] = 0 from t=0, 1 from t=1 s.

SwUp_in        = [0 0; 1 1];      % Up pressed at 1 s and held
SwDown_in      = [0 0; 20 0];     % Down never pressed
Vbat_in        = [0 12; 20 12];   % 12 V
MsgAge_in      = [0 0; 20 0];     % switch message always present

ObstacleActive = 0;               % 1 = hand in the window
ObstaclePos    = 70;              % obstacle position [%]
InitPos        = 50;              % window start position [%]
StallCurrent   = 10;              % motor current when blocked [A]
