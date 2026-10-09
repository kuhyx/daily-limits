package com.kuhy.daily_limits

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.SharedPreferences
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider

/**
 * One-line home-screen widget. Renders only what the Dart side saved
 * (home_widget_sync.dart): the line, and whether to grey it out because the
 * PC is offline or there is no data. Tapping it opens the app.
 */
class DailyLimitsWidget : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences,
    ) {
        val line = widgetData.getString("line", null) ?: "Daily limits: open the app"
        val offline = widgetData.getBoolean("offline", true)
        // text-on-dark / muted-on-dark from the unified tokens.
        val color = if (offline) 0xFFAAA09A.toInt() else 0xFFECEAE9.toInt()
        for (id in appWidgetIds) {
            val views = RemoteViews(context.packageName, R.layout.daily_limits_widget).apply {
                setTextViewText(R.id.widget_line, line)
                setTextColor(R.id.widget_line, color)
                setOnClickPendingIntent(
                    R.id.widget_root,
                    HomeWidgetLaunchIntent.getActivity(context, MainActivity::class.java),
                )
            }
            appWidgetManager.updateAppWidget(id, views)
        }
    }
}
