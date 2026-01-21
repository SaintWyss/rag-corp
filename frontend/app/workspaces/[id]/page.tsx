import { redirect } from "next/navigation";

type PageProps = {
  params: {
    id: string;
  };
};

export default function WorkspaceIndexRedirect({ params }: PageProps) {
  redirect(`/workspaces/${params.id}/documents`);
}
