package com.example.voiceguard;

import android.app.*;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import java.util.ArrayList;
import java.util.Locale;

public class CallService extends Service {
    private static final String TAG = "CallService";
    private static final String CHANNEL_ID = "CallServiceChannel";
    public static final String ACTION_STT_RESULT = "com.example.voiceguard.STT_RESULT";
    public static final String EXTRA_STT_TEXT = "stt_text";

    private SpeechRecognizer speechRecognizer;
    private Intent recognizerIntent;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("VoiceGuard 실시간 분석 중")
                .setContentText("통화 내용을 분석하여 피싱 여부를 감시하고 있습니다.")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .build();

        startForeground(1, notification);

        initSpeechRecognizer();
    }

    private void initSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        recognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.KOREAN.toString());
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);

        speechRecognizer.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle params) { Log.d(TAG, "onReadyForSpeech"); }
            @Override public void onBeginningOfSpeech() { Log.d(TAG, "onBeginningOfSpeech"); }
            @Override public void onRmsChanged(float rmsdB) {}
            @Override public void onBufferReceived(byte[] buffer) {}
            @Override public void onEndOfSpeech() { Log.d(TAG, "onEndOfSpeech"); }
            @Override public void onError(int error) {
                Log.e(TAG, "onError: " + error);
                // Restart if error occurs
                if (error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                    speechRecognizer.startListening(recognizerIntent);
                }
            }

            @Override
            public void onResults(Bundle results) {
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (matches != null && !matches.isEmpty()) {
                    String text = matches.get(0);
                    broadcastResult(text);
                }
                // Continue listening
                speechRecognizer.startListening(recognizerIntent);
            }

            @Override
            public void onPartialResults(Bundle partialResults) {
                ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (matches != null && !matches.isEmpty()) {
                    broadcastResult(matches.get(0));
                }
            }

            @Override public void onEvent(int eventType, Bundle params) {}
        });

        speechRecognizer.startListening(recognizerIntent);
    }

    private void broadcastResult(String text) {
        Intent intent = new Intent(ACTION_STT_RESULT);
        intent.putExtra(EXTRA_STT_TEXT, text);
        sendBroadcast(intent);

        // Also try to open SttAnalysisActivity if not already open
        Intent activityIntent = new Intent(this, SttAnalysisActivity.class);
        activityIntent.putExtra("stt_text", text);
        activityIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(activityIntent);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (speechRecognizer != null) {
            speechRecognizer.destroy();
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                    CHANNEL_ID,
                    "Call Analysis Service Channel",
                    NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }
}
