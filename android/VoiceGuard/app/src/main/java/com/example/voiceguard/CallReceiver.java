package com.example.voiceguard;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.telephony.TelephonyManager;
import android.util.Log;

public class CallReceiver extends BroadcastReceiver {
    private static final String TAG = "CallReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent.getAction().equals(TelephonyManager.ACTION_PHONE_STATE_CHANGED)) {
            String state = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
            Log.d(TAG, "Phone State Changed: " + state);

            if (TelephonyManager.EXTRA_STATE_OFFHOOK.equals(state)) {
                // Call started (or accepted)
                Intent serviceIntent = new Intent(context, CallService.class);
                context.startForegroundService(serviceIntent);
            } else if (TelephonyManager.EXTRA_STATE_IDLE.equals(state)) {
                // Call ended
                Intent serviceIntent = new Intent(context, CallService.class);
                context.stopService(serviceIntent);
            }
        }
    }
}
