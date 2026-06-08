import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import AlertCard from '../components/AlertCard';
import { getHistory } from '../services/historyService';
import type { AlertResponse } from '../types/alert';
import type { RootStackParamList } from './DashboardScreen';
import { useResponsive } from '../utils/responsive';

type HistoryNavProp = StackNavigationProp<RootStackParamList, 'History'>;

export default function HistoryScreen(): JSX.Element {
  const navigation = useNavigation<HistoryNavProp>();
  const [history, setHistory] = useState<AlertResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const { fontSizes } = useResponsive();

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      getHistory()
        .then(setHistory)
        .finally(() => setLoading(false));
    }, []),
  );

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#1a1a2e" />
      </View>
    );
  }

  if (history.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={[styles.emptyText, { fontSize: fontSizes.body }]}>Nenhum alerta visualizado ainda</Text>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.list}
      contentContainerStyle={styles.listContent}
      data={history}
      keyExtractor={(item) => item.event_id}
      renderItem={({ item }) => (
        <AlertCard
          alert={item}
          onPress={() =>
            navigation.navigate('AlertDetail', {
              alertId: item.event_id,
              alertData: item,
            })
          }
        />
      )}
    />
  );
}

const styles = StyleSheet.create({
  list: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    paddingVertical: 8,
  },
  listContent: {
    maxWidth: 600,
    alignSelf: 'center',
    width: '100%',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
  },
  emptyText: {
    color: '#888',
  },
});