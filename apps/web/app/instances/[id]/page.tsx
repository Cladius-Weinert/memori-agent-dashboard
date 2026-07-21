import InstanceDetail from "@/app/pages/instances/[id]";

export default function InstanceDetailRoute({ params }: { params: { id: string } }) {
  return <InstanceDetail params={params} />;
}