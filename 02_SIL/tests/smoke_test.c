/* Quick check: press Up with the window at 50 % and print what happens.
   Not the real test harness - that comes in Step 2c. */
#include <stdio.h>
#include "window_ctrl.h"

int main(void)
{
    WindowInputs_t  in  = { false, false, 50.0f, 0.0f, 12.0f, 0.0f };
    WindowOutputs_t out = { 0 };

    WindowCtrl_Init();

    for (int step = 0; step < 6; step++)
    {
        in.sw_up     = (step >= 2);              /* press Up at step 2 */
        in.current_a = (out.motor_cmd != 0) ? 2.0f : 0.0f;
        WindowCtrl_Step(&in, &out);
        printf("step %d: sw_up=%d  state=%d  motor_cmd=%d\n",
               step, in.sw_up, (int)out.state, out.motor_cmd);
    }
    return 0;
}
