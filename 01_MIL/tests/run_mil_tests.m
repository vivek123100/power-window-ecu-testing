function R = run_mil_tests()
% RUN_MIL_TESTS  Automatic MIL test harness for the power window ECU.
%   Runs every test case on PowerWindow_MIL.slx, checks the results
%   against the requirements, prints a summary, writes
%   reports/MIL_test_report.md and saves every run as CSV in
%   reports/b2b/mil/ (reference data for the SIL back-to-back test).
%
%   Usage (from the repo root or 01_MIL/tests):  R = run_mil_tests;

model = "PowerWindow_MIL";
load_system(model);

tests = defineTests();
R = struct("TC", {}, "Req", {}, "Description", {}, "Result", {}, "Details", {});

for i = 1:numel(tests)
    tc = tests(i);
    fprintf("Running %-6s ... ", tc.ID);

    if isempty(tc.Check)                       % not testable at MIL level
        R(end+1) = row(tc, "N/A", tc.Note); %#ok<AGROW>
        fprintf("N/A\n");
        continue
    end

    try
        in = Simulink.SimulationInput(model);
        in = in.setModelParameter("StopTime", num2str(tc.StopTime));
        in = in.setVariable("SwUp_in",        tc.SwUp);
        in = in.setVariable("SwDown_in",      tc.SwDown);
        in = in.setVariable("Vbat_in",        tc.Vbat);
        in = in.setVariable("MsgAge_in",      tc.MsgAge);
        in = in.setVariable("ObstacleActive", tc.ObstacleActive);
        in = in.setVariable("ObstaclePos",    tc.ObstaclePos);
        in = in.setVariable("InitPos",        tc.InitPos);
        in = in.setVariable("StallCurrent",   tc.StallCurrent);

        out = sim(in);
        r   = extractSignals(out);
        exportCsv(r, tc.ID);                   % reference data for back-to-back
        [ok, msg] = tc.Check(r);
        if ok, res = "PASS"; else, res = "FAIL"; end
    catch err
        res = "ERROR";
        msg = string(err.message);
    end

    R(end+1) = row(tc, res, msg); %#ok<AGROW>
    fprintf("%s  (%s)\n", res, msg);
end

T = struct2table(R);
disp(T);
nPass = sum(T.Result == "PASS");
nRun  = sum(T.Result ~= "N/A");
fprintf("\n%d of %d executed test cases passed.\n", nPass, nRun);
writeReport(T);
end

% =====================================================================
%  TEST CASE DEFINITIONS
%  Inputs are [time value] tables: [0 0; 1 1] = 0 from t=0, 1 from t=1 s.
% =====================================================================
function tests = defineTests()
up1   = [0 0; 1 1];          % Up pressed at 1 s and held
down1 = [0 0; 1 1];          % Down pressed at 1 s and held
off   = [0 0; 20 0];         % never pressed

tests = makeTest("TC_01", "REQ_01", "Up pressed -> motor up within 50 ms", @chk_TC01);
tests(end+1) = makeTest("TC_02", "REQ_04", "Window stops at 100 %", @chk_TC02);
tests(end+1) = makeTest("TC_03", "REQ_05", "Stall current 7.9 A -> no pinch", @chk_TC03, ...
    "ObstacleActive", 1, "StallCurrent", 7.9);
tests(end+1) = makeTest("TC_04", "REQ_05, REQ_06", "Stall current 8.1 A -> pinch, reverse >= 20 %", @chk_TC04, ...
    "ObstacleActive", 1, "StallCurrent", 8.1);
tests(end+1) = makeTest("TC_05", "REQ_07", "Blocked above 96 % -> no reversal", @chk_TC05, ...
    "InitPos", 97, "ObstacleActive", 1, "ObstaclePos", 98, "StallCurrent", 9);
tests(end+1) = makeTest("TC_06", "REQ_08", "Vbat 8.9 V -> motor stays off", @chk_motorNeverRuns, ...
    "Vbat", [0 8.9; 20 8.9]);
tests(end+1) = makeTest("TC_07", "REQ_08", "Vbat 9.0 V -> motor up", @chk_TC01, ...
    "Vbat", [0 9.0; 20 9.0]);
tests(end+1) = makeTest("TC_08", "REQ_09", "Switch message lost at 3 s -> stop + DTC", @chk_TC08, ...
    "MsgAge", [0 0; 3 600]);
tests(end+1) = makeTest("TC_09", "REQ_11", "Up and Down together -> motor stays off", @chk_motorNeverRuns, ...
    "SwDown", down1);
tests(end+1) = makeTest("TC_10", "REQ_02", "Down pressed -> motor down within 50 ms", @chk_TC10, ...
    "SwUp", off, "SwDown", down1);
tests(end+1) = makeTest("TC_11", "REQ_02, REQ_04", "Pos 0 %, Down -> motor stays off", @chk_motorNeverRuns, ...
    "SwUp", off, "SwDown", down1, "InitPos", 0);
tests(end+1) = makeTest("TC_12", "REQ_02", "Pos 1 %, Down -> motor down", @chk_TC10, ...
    "SwUp", off, "SwDown", down1, "InitPos", 1);
tests(end+1) = makeTest("TC_13", "REQ_03", "Up released at 2 s -> stop within 50 ms", @chk_releaseAt2, ...
    "SwUp", [0 0; 1 1; 2 0]);
tests(end+1) = makeTest("TC_14", "REQ_03", "Down released at 2 s -> stop within 50 ms", @chk_releaseAt2, ...
    "SwUp", off, "SwDown", [0 0; 1 1; 2 0]);
tests(end+1) = makeTest("TC_15", "REQ_10", "Blocked motor, 7.9 s -> still running, no DTC", @chk_TC15, ...
    "ObstacleActive", 1, "StallCurrent", 7.9);
tests(end+1) = makeTest("TC_16", "REQ_10", "Blocked motor, 8.1 s -> stop + DTC", @chk_TC16, ...
    "ObstacleActive", 1, "StallCurrent", 7.9);
tests(end+1) = makeTest("TC_17", "REQ_12", "Status message cycle time", [], ...
    "Note", "No CAN at MIL level - tested in CAN/HIL step");
tests(end+1) = makeTest("TC_18", "REQ_12", "Status message content", [], ...
    "Note", "No CAN at MIL level - tested in CAN/HIL step");
tests(end+1) = makeTest("TC_19", "REQ_12, REQ_14", "Pinch flag set during pinch", @chk_TC19, ...
    "ObstacleActive", 1);
tests(end+1) = makeTest("TC_20", "REQ_09", "Message lost during pinch reversal -> stop + DTC", @chk_TC20, ...
    "ObstacleActive", 1, "MsgAge", [0 0; 2 600]);
tests(end+1) = makeTest("TC_21", "REQ_13, REQ_14", "Up held after pinch -> no re-closing", @chk_TC21, ...
    "ObstacleActive", 1);
tests(end+1) = makeTest("TC_22", "REQ_09", "Message back while Up held -> no restart", @chk_TC22, ...
    "SwUp", [0 0; 1 1; 6 0], "MsgAge", [0 0; 3 600; 5 0]);
end

function tc = makeTest(id, req, desc, check, varargin)
% Default inputs: Up pressed at 1 s, 12 V, no obstacle, window at 50 %.
tc = struct("ID", id, "Req", req, "Description", desc, "Check", check, ...
    "SwUp", [0 0; 1 1], "SwDown", [0 0; 20 0], "Vbat", [0 12; 20 12], ...
    "MsgAge", [0 0; 20 0], "ObstacleActive", 0, "ObstaclePos", 70, ...
    "InitPos", 50, "StallCurrent", 10, "StopTime", 12, "Note", "");
for k = 1:2:numel(varargin)
    tc.(varargin{k}) = varargin{k+1};
end
end

% =====================================================================
%  CHECKS  -  each returns [ok, message]
% =====================================================================
function [ok, msg] = chk_TC01(r)
t = firstT(r.MotorCmd, @(v) v == 1, 1);
ok  = (t - 1) <= 0.05;
msg = sprintf("motor up after %.0f ms (limit 50 ms)", (t - 1) * 1000);
end

function [ok, msg] = chk_TC02(r)
p = valAt(r.Pos, 4);  c = valAt(r.MotorCmd, 4);
ok  = p >= 99.9 && c == 0;
msg = sprintf("at 4 s: Pos = %.1f %%, MotorCmd = %d", p, c);
end

function [ok, msg] = chk_TC03(r)
ok  = all(r.PinchFlag.v == 0) && all(r.MotorCmd.v ~= -1);
msg = sprintf("PinchFlag max = %d, reversal seen = %d", max(r.PinchFlag.v), any(r.MotorCmd.v == -1));
end

function [ok, msg] = chk_TC04(r)
tStall = firstT(r.Current, @(v) v > 8, 0);
tRev   = firstT(r.MotorCmd, @(v) v == -1, 0);
if isinf(tRev)
    ok = false; msg = "no reversal"; return
end
pMax = max(r.Pos.v(r.Pos.t <= tRev + 1e-6));
rev  = pMax - valAt(r.Pos, 4);
ok   = (tRev - tStall) <= 0.2 && rev >= 20 && any(r.PinchFlag.v == 1);
msg  = sprintf("reversal started %.0f ms after stall (limit 200 ms), reversed %.1f %%", ...
    (tRev - tStall) * 1000, rev);
end

function [ok, msg] = chk_TC05(r)
ok  = all(r.MotorCmd.v ~= -1) && all(r.PinchFlag.v == 0);
msg = sprintf("reversal seen = %d", any(r.MotorCmd.v == -1));
end

function [ok, msg] = chk_motorNeverRuns(r)
ok  = all(r.MotorCmd.v == 0);
msg = sprintf("MotorCmd min/max = %d / %d", min(r.MotorCmd.v), max(r.MotorCmd.v));
end

function [ok, msg] = chk_TC08(r)
before = valAt(r.DTC_SwitchTimeout, 2.9);
c      = valAt(r.MotorCmd, 3.1);
dtc    = valAt(r.DTC_SwitchTimeout, 3.1);
latch  = valAt(r.DTC_SwitchTimeout, 11);
ok  = before == 0 && c == 0 && dtc == 1 && latch == 1;
msg = sprintf("DTC before = %d, at 3.1 s: MotorCmd = %d, DTC = %d, DTC at 11 s = %d", before, c, dtc, latch);
end

function [ok, msg] = chk_TC10(r)
t = firstT(r.MotorCmd, @(v) v == -1, 1);
ok  = (t - 1) <= 0.05;
msg = sprintf("motor down after %.0f ms (limit 50 ms)", (t - 1) * 1000);
end

function [ok, msg] = chk_releaseAt2(r)
running = valAt(r.MotorCmd, 1.9) ~= 0;
t = firstT(r.MotorCmd, @(v) v == 0, 2);
ok  = running && (t - 2) <= 0.05;
msg = sprintf("running before release = %d, stopped %.0f ms after release (limit 50 ms)", running, (t - 2) * 1000);
end

function [ok, msg] = chk_TC15(r)
c = valAt(r.MotorCmd, 8.9);  d = valAt(r.DTC_MotorOverrun, 8.9);
ok  = c == 1 && d == 0;
msg = sprintf("at 8.9 s (7.9 s running): MotorCmd = %d, DTC = %d", c, d);
end

function [ok, msg] = chk_TC16(r)
c = valAt(r.MotorCmd, 9.1);  d = valAt(r.DTC_MotorOverrun, 9.1);
ok  = c == 0 && d == 1;
msg = sprintf("at 9.1 s (8.1 s running): MotorCmd = %d, DTC = %d", c, d);
end

function [ok, msg] = chk_TC19(r)
f = valAt(r.PinchFlag, 2.0);
ok  = f == 1;
msg = sprintf("PinchFlag at 2.0 s = %d", f);
end

function [ok, msg] = chk_TC20(r)
c = valAt(r.MotorCmd, 2.1);  d = valAt(r.DTC_SwitchTimeout, 2.1);
wasReversing = valAt(r.MotorCmd, 1.95) == -1;
ok  = wasReversing && c == 0 && d == 1;
msg = sprintf("reversing at 1.95 s = %d, at 2.1 s: MotorCmd = %d, DTC = %d", wasReversing, c, d);
end

function [ok, msg] = chk_TC21(r)
reclose = any(r.MotorCmd.v(r.MotorCmd.t > 2.7) == 1);
f = valAt(r.PinchFlag, 5);
ok  = ~reclose && f == 1;
msg = sprintf("re-closing after pinch = %d, PinchFlag at 5 s = %d", reclose, f);
end

function [ok, msg] = chk_TC22(r)
restart = any(r.MotorCmd.v(r.MotorCmd.t > 3.1) ~= 0);
d = valAt(r.DTC_SwitchTimeout, 11);
ok  = ~restart && d == 1;
msg = sprintf("motor moved after fault = %d, DTC at 11 s = %d", restart, d);
end

% =====================================================================
%  HELPERS
% =====================================================================
function r = extractSignals(out)
names = ["MotorCmd", "PinchFlag", "DTC_SwitchTimeout", "DTC_MotorOverrun", "Pos", "Current"];
for n = names
    ts = out.get(n);
    s.t = ts.Time(:);
    s.v = double(squeeze(ts.Data));
    s.v = s.v(:);
    r.(n) = s;
end
end

function v = valAt(s, t)
% Value of signal s at time t (last sample at or before t).
idx = find(s.t <= t + 1e-6, 1, "last");
v = s.v(idx);
end

function t = firstT(s, cond, t0)
% First time at or after t0 where cond(value) is true; Inf if never.
idx = find(s.t >= t0 - 1e-6 & cond(s.v), 1, "first");
if isempty(idx), t = Inf; else, t = s.t(idx); end
end

function exportCsv(r, id)
% Save all logged signals of one test run as CSV (MIL reference for B2B).
here = fileparts(mfilename("fullpath"));
d = fullfile(here, "..", "..", "reports", "b2b", "mil");
if ~isfolder(d), mkdir(d); end
T = table(r.MotorCmd.t, r.MotorCmd.v, r.PinchFlag.v, r.DTC_SwitchTimeout.v, ...
    r.DTC_MotorOverrun.v, r.Pos.v, r.Current.v, 'VariableNames', ...
    ["t", "motor_cmd", "pinch_flag", "dtc_switch_timeout", ...
     "dtc_motor_overrun", "pos", "current"]);
writetable(T, fullfile(d, id + ".csv"));
end

function x = row(tc, res, msg)
x = struct("TC", string(tc.ID), "Req", string(tc.Req), ...
    "Description", string(tc.Description), "Result", string(res), "Details", string(msg));
end

function writeReport(T)
here = fileparts(mfilename("fullpath"));
repDir = fullfile(here, "..", "..", "reports");
if ~isfolder(repDir), mkdir(repDir); end
f = fullfile(repDir, "MIL_test_report.md");
fid = fopen(f, "w");
fprintf(fid, "# MIL Test Report - Power Window ECU\n\n");
fprintf(fid, "Generated: %s  \nModel: PowerWindow_MIL.slx\n\n", string(datetime("now")));
fprintf(fid, "**%d of %d executed test cases passed.**\n\n", ...
    sum(T.Result == "PASS"), sum(T.Result ~= "N/A"));
fprintf(fid, "| TC | Requirement | Description | Result | Details |\n|---|---|---|---|---|\n");
for i = 1:height(T)
    fprintf(fid, "| %s | %s | %s | %s | %s |\n", T.TC(i), T.Req(i), T.Description(i), T.Result(i), T.Details(i));
end
fclose(fid);
fprintf("Report written to %s\n", f);
end
