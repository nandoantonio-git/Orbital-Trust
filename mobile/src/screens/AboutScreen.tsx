import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useResponsive } from '../utils/responsive';

const MAIN_TEXT =
  'O Orbital Trust transforma imagens orbitais e evidências visuais em alertas ambientais claros, ajudando pessoas e equipes a entender o que mudou em uma área e se o dado analisado é confiável para apoiar uma decisão.';

const HOW_IT_WORKS_STEPS = [
  '1. O módulo IoT analisa frames de vídeo ou imagens orbitais.',
  '2. O sistema identifica padrões como vegetação, solo exposto, água, queimada ou baixa visibilidade.',
  '3. A API/ML transforma essas evidências em risco, confiança e recomendação.',
  '4. O app apresenta o alerta, a explicação e o histórico de análises.',
];

const WHY_IT_MATTERS =
  'Dados espaciais são poderosos, mas nem sempre são fáceis de interpretar. Nuvens, sombras, ruídos e baixa qualidade visual podem afetar uma análise. Por isso, o Orbital Trust não mostra apenas o alerta: ele também mostra o nível de confiança do dado.';

const TRANSPARENCY =
  'O índice de confiança não representa certeza absoluta. Ele indica a qualidade da evidência visual disponível para apoiar a análise. Decisões críticas devem considerar validação humana e outras fontes de dados.';

export default function AboutScreen(): JSX.Element {
  const { fontSizes, spacing } = useResponsive();

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[
        styles.content,
        { padding: spacing.md, paddingBottom: spacing.lg },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { fontSize: fontSizes.h2 }]}>
          Orbital Trust
        </Text>
        <Text style={[styles.subtitle, { fontSize: fontSizes.body }]}>
          Alertas ambientais confiáveis com visão computacional
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.bodyText, { fontSize: fontSizes.body }]}>
          {MAIN_TEXT}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>
          Como funciona
        </Text>
        {HOW_IT_WORKS_STEPS.map((step) => (
          <Text
            key={step}
            style={[styles.stepText, { fontSize: fontSizes.body }]}
          >
            {step}
          </Text>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>
          Por que isso importa
        </Text>
        <Text style={[styles.bodyText, { fontSize: fontSizes.body }]}>
          {WHY_IT_MATTERS}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>
          Transparência
        </Text>
        <Text style={[styles.bodyText, { fontSize: fontSizes.body }]}>
          {TRANSPARENCY}
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    maxWidth: 600,
    alignSelf: 'center',
    width: '100%',
  },
  header: {
    marginBottom: 16,
  },
  title: {
    color: '#1a1a2e',
    fontWeight: '700',
    marginBottom: 6,
  },
  subtitle: {
    color: '#555',
    lineHeight: 22,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  sectionTitle: {
    color: '#1a1a2e',
    fontWeight: '600',
    marginBottom: 10,
  },
  bodyText: {
    color: '#333',
    lineHeight: 22,
  },
  stepText: {
    color: '#333',
    lineHeight: 22,
    marginBottom: 8,
  },
});
