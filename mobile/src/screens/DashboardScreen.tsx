import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import AlertCard from '../components/AlertCard';
import { getAlerts } from '../services/alertService';
import {
  getPipelineStatus,
  startPipeline,
  stopPipeline,
} from '../services/pipelineService';
import type { PipelineStatus } from '../services/pipelineService';
import type { AlertResponse } from '../types/alert';
import { useResponsive } from '../utils/responsive';

export type RootStackParamList = {
  Dashboard: undefined;
  AlertDetail: { alertId: string; alertData?: AlertResponse };
  History: undefined;
  Settings: undefined;
  About: undefined;
};

type DashboardNavProp = StackNavigationProp<RootStackParamList, 'Dashboard'>;

const POLL_INTERVAL_MS = 3000; // recarrega alertas a cada 3s enquanto pipeline roda

export default function DashboardScreen(): JSX.Element {
  const navigation = useNavigation<DashboardNavProp>();
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { fontSizes } = useResponsive();

  // carrega alertas
  const loadAlerts = useCallback(() => {
    getAlerts()
      .then(setAlerts)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  // polling enquanto pipeline está rodando
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(() => {
      loadAlerts();
      getPipelineStatus()
        .then(setPipeline)
        .catch(() => undefined);
    }, POLL_INTERVAL_MS);
  }, [loadAlerts]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    loadAlerts();
    // verifica estado inicial do pipeline
    getPipelineStatus()
      .then((status) => {
        setPipeline(status);
        if (status.running) startPolling();
      })
      .catch(() => undefined);

    return () => stopPolling();
  }, [loadAlerts, startPolling, stopPolling]);

  // para polling quando pipeline termina
  useEffect(() => {
    if (pipeline && !pipeline.running) {
      stopPolling();
      loadAlerts(); // carrega final
    }
  }, [pipeline, stopPolling, loadAlerts]);

  const handlePipelineToggle = async () => {
    if (pipelineLoading) return;
    setPipelineLoading(true);

    try {
      if (pipeline?.running) {
        await stopPipeline();
        setPipeline((p) => p ? { ...p, running: false } : p);
        stopPolling();
        loadAlerts();
      } else {
        const status = await startPipeline();
        setPipeline(status);
        startPolling();
      }
    } catch {
      // silencia erro — botão volta ao estado anterior
    } finally {
      setPipelineLoading(false);
    }
  };

  const isRunning = pipeline?.running ?? false;

  return (
    <View style={styles.container}>
      {/* Botão de pipeline */}
      <View style={styles.pipelineBar}>
        <View style={styles.pipelineInfo}>
          {pipeline && (
            <Text style={[styles.pipelineText, { fontSize: fontSizes.caption }]}>
              {isRunning
                ? `Analisando... ${pipeline.payload_count} payload${pipeline.payload_count !== 1 ? 's' : ''}`
                : pipeline.payload_count > 0
                ? `Concluído — ${pipeline.payload_count} payloads gerados`
                : 'Pipeline inativo'}
            </Text>
          )}
        </View>
        <TouchableOpacity
          style={[
            styles.pipelineButton,
            isRunning ? styles.pipelineButtonStop : styles.pipelineButtonStart,
            pipelineLoading && styles.pipelineButtonDisabled,
          ]}
          onPress={handlePipelineToggle}
          disabled={pipelineLoading}
        >
          {pipelineLoading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={[styles.pipelineButtonText, { fontSize: fontSizes.label }]}>
              {isRunning ? '⏹ Parar' : '▶ Analisar Vídeo'}
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Lista de alertas */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#1a1a2e" />
        </View>
      ) : alerts.length === 0 ? (
        <View style={styles.centered}>
          <Text style={[styles.emptyText, { fontSize: fontSizes.body }]}>
            Nenhum alerta encontrado.
          </Text>
          <Text style={[styles.emptyHint, { fontSize: fontSizes.caption }]}>
            Toque em "Analisar Vídeo" para iniciar o pipeline.
          </Text>
        </View>
      ) : (
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
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  pipelineBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
    gap: 12,
  },
  pipelineInfo: {
    flex: 1,
  },
  pipelineText: {
    color: '#555',
  },
  pipelineButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    minWidth: 140,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 36,
  },
  pipelineButtonStart: {
    backgroundColor: '#1a1a2e',
  },
  pipelineButtonStop: {
    backgroundColor: '#b91c1c',
  },
  pipelineButtonDisabled: {
    opacity: 0.6,
  },
  pipelineButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  list: {
    flex: 1,
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
    gap: 8,
  },
  emptyText: {
    color: '#888',
  },
  emptyHint: {
    color: '#aaa',
    textAlign: 'center',
    paddingHorizontal: 32,
  },
});