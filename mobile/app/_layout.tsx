import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: "#4A90D9",
          },
          headerTintColor: "#fff",
          headerTitleStyle: {
            fontWeight: "bold",
            fontSize: 20,
          },
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            title: "信息鉴别助手",
          }}
        />
        <Stack.Screen
          name="result"
          options={{
            title: "分析结果",
          }}
        />
      </Stack>
    </>
  );
}
