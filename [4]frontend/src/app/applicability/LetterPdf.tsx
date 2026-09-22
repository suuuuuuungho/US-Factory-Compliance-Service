// SUU-254: AskResult → 편지 한 장짜리 PDF. EPA applicability determination letter 모양을 따르되 면책이 맨 앞.
import { Document, Page, StyleSheet, Text, View } from "@react-pdf/renderer";
import type { AskResult } from "@/lib/api";

const s = StyleSheet.create({
  page: { fontFamily: "Times-Roman", fontSize: 11, padding: 56, lineHeight: 1.4 },
  box: { borderWidth: 2, borderColor: "#000", padding: 10, marginBottom: 18 },
  boxText: { fontFamily: "Times-Bold", fontSize: 14, textAlign: "center" },
  line: { marginBottom: 6 },
  heading: { fontFamily: "Times-Bold", fontSize: 12, marginTop: 14, marginBottom: 4 },
  item: { marginLeft: 12, marginBottom: 3 },
  cite: { marginLeft: 24, color: "#444" },
  noteTitle: { fontFamily: "Times-Bold", marginLeft: 12, marginBottom: 3 },
  footer: { marginTop: 24, fontSize: 9, color: "#444" },
});

// SUU-255: memo(제목+본문)가 있으면 편지 끝에 Notes 절. 둘 다 비어 있으면 절 자체를 생략.
export function LetterPdf({
  question,
  result,
  memo,
}: {
  question: string;
  result: AskResult;
  memo?: { title: string; body: string };
}) {
  const date = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const candidates = result.answer?.candidates ?? [];
  const checklist = result.answer?.checklist ?? [];
  const notes = memo && (memo.title.trim() !== "" || memo.body.trim() !== "") ? memo : null;
  return (
    <Document>
      <Page size="LETTER" style={s.page}>
        <View style={s.box}>
          <Text style={s.boxText}>
            This document is NOT a legal determination. It is an AI-generated reference only and does not
            represent the position of the U.S. EPA or any regulatory agency.
          </Text>
        </View>
        <Text style={s.line}>{date}</Text>
        <Text style={s.line}>To: [Facility]</Text>
        <Text style={s.line}>Re: {question}</Text>

        <Text style={s.heading}>Candidate Subparts (40 CFR Part 63)</Text>
        {candidates.map((c) => (
          <View key={c.subpart} style={s.item}>
            <Text>Subpart {c.subpart} — {c.title}</Text>
            {c.criteria.map((cr, i) => (
              <View key={i} style={s.item}>
                <Text>• {cr.criterion}</Text>
                {cr.citations.map((ci) => <Text key={ci} style={s.cite}>{ci}</Text>)}
              </View>
            ))}
          </View>
        ))}

        <Text style={s.heading}>Checklist</Text>
        {checklist.map((q, i) => <Text key={i} style={s.item}>{i + 1}. {q}</Text>)}

        <Text style={s.heading}>Related Sections</Text>
        {result.sections.map((sec) => (
          <Text key={sec.section_key} style={s.item}>{sec.section_key} (Subpart {sec.subpart})</Text>
        ))}

        {notes && (
          <>
            <Text style={s.heading}>Notes</Text>
            {notes.title.trim() !== "" && <Text style={s.noteTitle}>{notes.title}</Text>}
            {notes.body.trim() !== "" && <Text style={s.item}>{notes.body}</Text>}
          </>
        )}

        <Text style={s.footer}>For reference only — not a legal determination. Consult qualified counsel or the regulatory agency.</Text>
      </Page>
    </Document>
  );
}
