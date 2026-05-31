import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import AlertCard from '../components/AlertCard';
import { getAlerts } from '../services/alertService';
import type { AlertResponse } from '../types/alert';
import { useResponsive } from '../utils/responsive';

export type RootStackParamList = {
  Dashboard: undefined;
  AlertDetail: { alertId: string };
  History: undefined;
  Settings: undefined;
  About: undefined;
};

type DashboardNavProp = StackNavigationProp<RootStackParamList, 'Dashboard'>;

export default function DashboardScreen(): JSX.Element {
  const navigation = useNavigation<DashboardNavProp>();
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const { fontSizes } = useResponsive();

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#1a1a2e" />
      </View>
    );
  }

  if (alerts.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={[styles.emptyText, { fontSize: fontSizes.body }]}>Nenhum alerta encontrado.</Text>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.list}
      contentContainerStyle={styles.listContent}
      data={alerts}
      keyExtractor={(item) => item.event_id}
      renderItem={({ item }) => (
        <AlertCard
          alert={item}
          onPress={() =>
            navigation.navigate('AlertDetail', { alertId: item.event_id })
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
