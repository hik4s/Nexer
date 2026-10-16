import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecipeField } from "./RecipeField";

describe("Explicit execution choices", () => {
  it("does not infer an empty multiselect from loaded options", async () => {
    const change = vi.fn();
    render(<RecipeField name="regions" declaration={{type: "array", allow_empty: true, field: {control: "multiselect"}}}
      value={undefined} catalog={{options: [{value: "new", label: "Nova região", disabled: false}], error: null}} onChange={change} />);
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Confirmar regions sem seleção"}));
    expect(change).toHaveBeenCalledWith("[]");
  });
  it("requires an explicit decision for an unchecked checkbox", async () => {
    const change = vi.fn();
    render(<RecipeField name="flag" declaration={{type: "boolean", field: {control: "checkbox"}}} value={undefined} onChange={change} />);
    expect(screen.getByRole("checkbox")).toBePartiallyChecked();
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Definir flag como desmarcado"}));
    expect(change).toHaveBeenCalledWith("false");
  });
  it("allows confirming the browser's color without implying a recorded default", async () => {
    const change = vi.fn();
    render(<RecipeField name="color" declaration={{type: "string", field: {control: "color"}}} value={undefined} onChange={change} />);
    expect(change).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", {name: "Confirmar color"}));
    expect(change).toHaveBeenCalledWith("#000000");
  });
  it("uses the configured display name while keeping the parameter identity", async () => {
    const change = vi.fn();
    render(<RecipeField name="input_001" declaration={{type: "string", label: "Email do responsável", field: {control: "email", max_length: 80}}} value="" onChange={change} />);
    const field = screen.getByLabelText("Email do responsável");
    expect(field).toHaveAttribute("id", "parameter-input_001");
    expect(field).toHaveAttribute("type", "email");
    await userEvent.setup().type(field, "a");
    expect(change).toHaveBeenCalledWith("a");
  });

  it("renders a native date-and-time picker while sending the masked value expected by the site", async () => {
    const change = vi.fn();
    render(<RecipeField name="input_001" declaration={{type:"string",label:"Data Hora Início",
      field:{control:"datetime-local",site_format:"dd/MM/yyyy HH:mm:ss"}}}
      value={"01/09/2026 00:00:00"} onChange={change}/>);
    const input = screen.getByLabelText("Data Hora Início");
    expect(input).toHaveAttribute("type","datetime-local");
    expect(input).toHaveValue("2026-09-01T00:00");
    fireEvent.change(input,{target:{value:"2026-10-31T23:59:00"}});
    expect(change).toHaveBeenLastCalledWith("31/10/2026 23:59:00");
    expect(screen.getByText(/Formato enviado ao site: dd\/MM\/yyyy HH:mm:ss/)).toBeInTheDocument();
  });
  it("keeps normal date variables in ISO format and leaves unrelated text inputs alone", () => {
    const change=vi.fn();
    const {rerender}=render(<RecipeField name="period_start" declaration={{type:"string",format:"date",field:{control:"date"}}}
      value="2026-09-01" onChange={change}/>);
    expect(screen.getByLabelText("Data inicial")).toHaveAttribute("type","date");
    rerender(<RecipeField name="remarks" declaration={{type:"string",field:{control:"text"}}}
      value="dd/mm/yyyy hh:mm" onChange={change}/>);
    expect(screen.getByLabelText("remarks")).toHaveAttribute("type","text");
  });
  it("never converts an invalid calendar value into a different date", () => {
    const change=vi.fn();
    render(<RecipeField name="input_002" declaration={{type:"string",label:"Data Hora Fim",
      field:{control:"datetime-local",site_format:"dd/MM/yyyy HH:mm:ss"}}}
      value="31/02/2026 11:00:00" onChange={change}/>);
    expect(screen.getByLabelText("Data Hora Fim")).toHaveValue("");
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(change).not.toHaveBeenCalled();
  });
});
