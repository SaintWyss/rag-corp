import { render, screen } from "@testing-library/react";
import AdminUsersPage from "../../../app/(app)/admin/users/page";
import { getCurrentUser, listUsers, listWorkspaces } from "@/shared/api/api";

jest.mock("@/shared/lib/apiKey", () => ({
  getStoredApiKey: jest.fn(),
  setStoredApiKey: jest.fn(),
}));

jest.mock("@/shared/api/api", () => ({
  getCurrentUser: jest.fn(),
  listUsers: jest.fn(),
  listWorkspaces: jest.fn(),
  createUser: jest.fn(),
  disableUser: jest.fn(),
  resetUserPassword: jest.fn(),
}));

describe("Admin Users Page", () => {
  beforeEach(() => {
    (listWorkspaces as jest.Mock).mockResolvedValue({ workspaces: [] });
  });

  it("blocks non-admin users", async () => {
    (getCurrentUser as jest.Mock).mockResolvedValue({
      id: "user-1",
      email: "employee@example.com",
      role: "employee",
      is_active: true,
    });

    render(<AdminUsersPage />);

    expect(await screen.findByTestId("admin-users-denied")).toBeInTheDocument();
  });

  it("renders user list for admins", async () => {
    (getCurrentUser as jest.Mock).mockResolvedValue({
      id: "admin-1",
      email: "admin@example.com",
      role: "admin",
      is_active: true,
    });
    (listUsers as jest.Mock).mockResolvedValue({
      users: [
        {
          id: "user-2",
          email: "empleado@example.com",
          role: "employee",
          is_active: true,
          created_at: "2026-01-14T22:00:00Z",
        },
      ],
    });

    render(<AdminUsersPage />);

    expect(
      await screen.findByRole("heading", { name: "Usuarios" })
    ).toBeInTheDocument();
    expect(await screen.findByText("empleado@example.com")).toBeInTheDocument();
  });
});
