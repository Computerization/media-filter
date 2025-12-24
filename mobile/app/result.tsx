import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { getVerdictColor, getVerdictText } from "@/lib/api";

export default function ResultScreen() {
  const params = useLocalSearchParams<{
    title: string;
    verdict: string;
    verdict_emoji: string;
    summary: string;
    details: string;
  }>();

  const verdictColor = getVerdictColor(params.verdict);
  const verdictText = getVerdictText(params.verdict);

  return (
    <ScrollView style={styles.container}>
      {/* Verdict Card */}
      <View style={[styles.verdictCard, { borderColor: verdictColor }]}>
        <Text style={styles.verdictEmoji}>{params.verdict_emoji}</Text>
        <Text style={[styles.verdictText, { color: verdictColor }]}>
          {verdictText}
        </Text>
      </View>

      {/* Title */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>文章标题</Text>
        <Text style={styles.titleText}>{params.title}</Text>
      </View>

      {/* Summary */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>简要说明</Text>
        <View
          style={[styles.summaryBox, { backgroundColor: verdictColor + "15" }]}
        >
          <Text style={styles.summaryText}>{params.summary}</Text>
        </View>
      </View>

      {/* Details */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>详细分析</Text>
        <Text style={styles.detailsText}>{params.details}</Text>
      </View>

      {/* Tips based on verdict */}
      <View style={styles.tipsSection}>
        <Text style={styles.tipsTitle}>温馨提示</Text>
        {params.verdict === "reliable" && (
          <Text style={styles.tipsText}>
            这篇文章看起来比较可信，但仍建议多方核实重要信息。
          </Text>
        )}
        {params.verdict === "caution" && (
          <Text style={styles.tipsText}>
            这篇文章存在一些疑点，建议：{"\n"}• 不要轻易转发{"\n"}•
            不要根据文章内容购买产品{"\n"}• 如有健康问题，请咨询医生
          </Text>
        )}
        {params.verdict === "misleading" && (
          <Text style={styles.tipsText}>
            这篇文章可能包含虚假信息，强烈建议：{"\n"}• 不要相信文章内容{"\n"}•
            不要转发给他人{"\n"}• 不要购买推荐的产品{"\n"}•
            如已转发，请告知收到的人
          </Text>
        )}
      </View>

      {/* Back Button */}
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backButtonText}>← 返回继续检测</Text>
      </TouchableOpacity>

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F5",
  },
  verdictCard: {
    backgroundColor: "#fff",
    margin: 20,
    marginBottom: 16,
    padding: 24,
    borderRadius: 16,
    alignItems: "center",
    borderWidth: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  verdictEmoji: {
    fontSize: 64,
    marginBottom: 8,
  },
  verdictText: {
    fontSize: 28,
    fontWeight: "bold",
  },
  section: {
    backgroundColor: "#fff",
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
  },
  sectionTitle: {
    fontSize: 16,
    color: "#6B7280",
    marginBottom: 8,
    fontWeight: "500",
  },
  titleText: {
    fontSize: 18,
    color: "#333",
    fontWeight: "600",
    lineHeight: 26,
  },
  summaryBox: {
    padding: 12,
    borderRadius: 8,
  },
  summaryText: {
    fontSize: 18,
    color: "#333",
    fontWeight: "500",
    lineHeight: 26,
  },
  detailsText: {
    fontSize: 17,
    color: "#333",
    lineHeight: 28,
  },
  tipsSection: {
    backgroundColor: "#FEF3C7",
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: "#F59E0B",
  },
  tipsTitle: {
    fontSize: 16,
    color: "#92400E",
    fontWeight: "bold",
    marginBottom: 8,
  },
  tipsText: {
    fontSize: 16,
    color: "#78350F",
    lineHeight: 26,
  },
  backButton: {
    backgroundColor: "#4A90D9",
    marginHorizontal: 20,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  backButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  bottomPadding: {
    height: 40,
  },
});
