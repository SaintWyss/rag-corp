import { redirect } from "next/navigation";
import Home from "../app/page";

jest.mock("next/navigation", () => ({
    redirect: jest.fn(),
}));

describe("Home Page", () => {
    it("redirects to login", () => {
        Home();
        expect(redirect).toHaveBeenCalledWith("/login");
    });
});
