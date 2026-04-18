import { CaseDetailPageContent } from "@/features/cases/components/CaseDetailPageContent";

export default async function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CaseDetailPageContent caseId={id} />;
}
