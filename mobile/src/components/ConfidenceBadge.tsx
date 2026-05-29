import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

interface Props {
  confidence: number;
}

function getBadgeColor(confidence: number): string {
  if (confidence >= 0.8) return '#22c55e';
  if (confidence >= 0.5) return '#eab308';
  return '#ef4444';
}

export default function ConfidenceBadge({ confidence }: Props): JSX.Element {
  const color = getBadgeColor(confidence);
  const label = `${Math.round(confidence * 100)}%`;

  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
});
