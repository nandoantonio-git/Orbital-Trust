import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import type { LinkingOptions } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import DashboardScreen from './src/screens/DashboardScreen';
import AlertDetailScreen from './src/screens/AlertDetailScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import type { RootStackParamList } from './src/screens/DashboardScreen';

const Stack = createStackNavigator<RootStackParamList>();

const linking: LinkingOptions<RootStackParamList> = {
  prefixes: [], // prefixes not used on web
  config: {
    screens: {
      Dashboard: '',
      AlertDetail: 'alerts/:alertId',
      History: 'history',
    },
  },
};

export default function App(): JSX.Element {
  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator initialRouteName="Dashboard">
        <Stack.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={({ navigation }) => ({
            title: 'Orbital Trust',
            headerRight: () => (
              <TouchableOpacity
                onPress={() => navigation.navigate('History')}
                style={{ marginRight: 16, paddingHorizontal: 12, paddingVertical: 8, minHeight: 44, justifyContent: 'center' }}
              >
                <Text style={{ color: '#1a1a2e', fontSize: 14 }}>Histórico</Text>
              </TouchableOpacity>
            ),
          })}
        />
        <Stack.Screen
          name="AlertDetail"
          component={AlertDetailScreen}
          options={{ title: 'Detalhe do Alerta' }}
        />
        <Stack.Screen
          name="History"
          component={HistoryScreen}
          options={{ title: 'Histórico' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
