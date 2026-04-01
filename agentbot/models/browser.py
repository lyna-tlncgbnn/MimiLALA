"""Models for browser subgraph planning and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


BrowserActionType = Literal[
    "navigate",
    "click",
    "input",
    "scroll",
    "scroll_to_text",
    "wait",
    "go_back",
    "extract",
    "search_page",
    "find_elements",
    "switch_tab",
    "close_tab",
    "send_keys",
    "read_content",
    "get_dropdown_options",
    "select_dropdown_option",
    "screenshot",
    "save_as_pdf",
    "upload_file",
    "done",
]
BrowserRunStatus = Literal["running", "completed", "failed"]


class BrowserActionPlan(BaseModel):
    """Single-step action planned by the browser subgraph."""

    action_type: BrowserActionType
    reason: str = Field(min_length=1)
    url: str | None = None
    new_tab: bool = False
    index: int | None = Field(default=None, ge=1)
    text: str | None = None
    path: str | None = None
    clear: bool = True
    seconds: int | None = Field(default=None, ge=1, le=30)
    pages: float | None = Field(default=None, ge=0.1, le=10.0)
    down: bool = True
    query: str | None = None
    pattern: str | None = None
    selector: str | None = None
    attributes: list[str] | None = None
    include_text: bool = True
    extract_links: bool = False
    start_from_char: int = Field(default=0, ge=0)
    tab_id: str | None = Field(default=None, min_length=4, max_length=4)
    keys: str | None = None
    goal: str | None = None
    source: str | None = None
    context: str | None = None
    file_name: str | None = None
    print_background: bool = True
    landscape: bool = False
    scale: float = Field(default=1.0, ge=0.1, le=2.0)
    paper_format: str | None = None
    final_response: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "BrowserActionPlan":
        if self.action_type == "navigate" and not self.url:
            raise ValueError("navigate action requires url")
        if self.action_type == "upload_file":
            if self.index is None:
                raise ValueError("upload_file action requires index")
            if not self.path:
                raise ValueError("upload_file action requires path")
        if self.action_type == "click" and self.index is None:
            raise ValueError("click action requires index")
        if self.action_type == "input":
            if self.index is None:
                raise ValueError("input action requires index")
            if self.text is None:
                raise ValueError("input action requires text")
        if self.action_type == "scroll":
            if self.pages is None:
                raise ValueError("scroll action requires pages")
        if self.action_type == "scroll_to_text" and not self.text:
            raise ValueError("scroll_to_text action requires text")
        if self.action_type == "wait" and self.seconds is None:
            raise ValueError("wait action requires seconds")
        if self.action_type == "extract" and not self.query:
            raise ValueError("extract action requires query")
        if self.action_type == "search_page" and not self.pattern:
            raise ValueError("search_page action requires pattern")
        if self.action_type == "find_elements" and not self.selector:
            raise ValueError("find_elements action requires selector")
        if self.action_type == "switch_tab" and not self.tab_id:
            raise ValueError("switch_tab action requires tab_id")
        if self.action_type == "close_tab" and not self.tab_id:
            raise ValueError("close_tab action requires tab_id")
        if self.action_type == "send_keys" and not self.keys:
            raise ValueError("send_keys action requires keys")
        if self.action_type == "read_content" and not self.goal:
            raise ValueError("read_content action requires goal")
        if self.action_type == "get_dropdown_options" and self.index is None:
            raise ValueError("get_dropdown_options action requires index")
        if self.action_type == "select_dropdown_option":
            if self.index is None:
                raise ValueError("select_dropdown_option action requires index")
            if self.text is None:
                raise ValueError("select_dropdown_option action requires text")
        if self.action_type == "done" and not self.final_response:
            raise ValueError("done action requires final_response")
        return self


class BrowserNavigatePayload(BaseModel):
    url: str
    new_tab: bool = False


class BrowserClickPayload(BaseModel):
    index: int = Field(ge=1)


class BrowserInputPayload(BaseModel):
    index: int = Field(ge=1)
    text: str
    clear: bool = True


class BrowserUploadFilePayload(BaseModel):
    index: int = Field(ge=1)
    path: str


class BrowserScrollPayload(BaseModel):
    down: bool = True
    pages: float = Field(default=1.0, ge=0.1, le=10.0)
    index: int | None = Field(default=None, ge=0)


class BrowserWaitPayload(BaseModel):
    seconds: int = Field(default=3, ge=1, le=30)


class BrowserGoBackPayload(BaseModel):
    description: str | None = None


class BrowserExtractPayload(BaseModel):
    query: str
    extract_links: bool = False
    start_from_char: int = Field(default=0, ge=0)


class BrowserSearchPagePayload(BaseModel):
    pattern: str


class BrowserFindElementsPayload(BaseModel):
    selector: str
    attributes: list[str] | None = None
    include_text: bool = True


class BrowserSwitchTabPayload(BaseModel):
    tab_id: str = Field(min_length=4, max_length=4)


class BrowserSendKeysPayload(BaseModel):
    keys: str


class BrowserReadContentPayload(BaseModel):
    goal: str
    source: str = "page"
    context: str = ""


class BrowserCloseTabPayload(BaseModel):
    tab_id: str = Field(min_length=4, max_length=4)


class BrowserGetDropdownOptionsPayload(BaseModel):
    index: int = Field(ge=1)


class BrowserSelectDropdownOptionPayload(BaseModel):
    index: int = Field(ge=1)
    text: str


class BrowserScrollToTextPayload(BaseModel):
    text: str


class BrowserScreenshotPayload(BaseModel):
    file_name: str | None = None


class BrowserSaveAsPdfPayload(BaseModel):
    file_name: str | None = None
    print_background: bool = True
    landscape: bool = False
    scale: float = Field(default=1.0, ge=0.1, le=2.0)
    paper_format: str = "Letter"


class BrowserDonePayload(BaseModel):
    text: str = Field(min_length=1)
    success: bool = True


class BrowserPlannerAction(BaseModel):
    navigate: BrowserNavigatePayload | None = None
    click: BrowserClickPayload | None = None
    input: BrowserInputPayload | None = None
    upload_file: BrowserUploadFilePayload | None = None
    scroll: BrowserScrollPayload | None = None
    scroll_to_text: BrowserScrollToTextPayload | None = None
    wait: BrowserWaitPayload | None = None
    go_back: BrowserGoBackPayload | None = None
    extract: BrowserExtractPayload | None = None
    search_page: BrowserSearchPagePayload | None = None
    find_elements: BrowserFindElementsPayload | None = None
    switch_tab: BrowserSwitchTabPayload | None = None
    close_tab: BrowserCloseTabPayload | None = None
    send_keys: BrowserSendKeysPayload | None = None
    read_content: BrowserReadContentPayload | None = None
    get_dropdown_options: BrowserGetDropdownOptionsPayload | None = None
    select_dropdown_option: BrowserSelectDropdownOptionPayload | None = None
    screenshot: BrowserScreenshotPayload | None = None
    save_as_pdf: BrowserSaveAsPdfPayload | None = None
    done: BrowserDonePayload | None = None

    @model_validator(mode="after")
    def validate_single_action(self) -> "BrowserPlannerAction":
        populated = [
            name
            for name in (
                "navigate",
                "click",
                "input",
                "upload_file",
                "scroll",
                "scroll_to_text",
                "wait",
                "go_back",
                "extract",
                "search_page",
                "find_elements",
                "switch_tab",
                "close_tab",
                "send_keys",
                "read_content",
                "get_dropdown_options",
                "select_dropdown_option",
                "screenshot",
                "save_as_pdf",
                "done",
            )
            if getattr(self, name) is not None
        ]
        if len(populated) != 1:
            raise ValueError("Planner action must contain exactly one action payload.")
        return self

    def to_execution_plan(self, reason: str) -> BrowserActionPlan:
        if self.navigate is not None:
            return BrowserActionPlan(
                action_type="navigate",
                reason=reason,
                url=self.navigate.url,
                new_tab=self.navigate.new_tab,
            )
        if self.click is not None:
            return BrowserActionPlan(action_type="click", reason=reason, index=self.click.index)
        if self.input is not None:
            return BrowserActionPlan(
                action_type="input",
                reason=reason,
                index=self.input.index,
                text=self.input.text,
                clear=self.input.clear,
            )
        if self.upload_file is not None:
            return BrowserActionPlan(
                action_type="upload_file",
                reason=reason,
                index=self.upload_file.index,
                path=self.upload_file.path,
            )
        if self.scroll is not None:
            return BrowserActionPlan(
                action_type="scroll",
                reason=reason,
                pages=self.scroll.pages,
                down=self.scroll.down,
                index=self.scroll.index,
            )
        if self.scroll_to_text is not None:
            return BrowserActionPlan(
                action_type="scroll_to_text",
                reason=reason,
                text=self.scroll_to_text.text,
            )
        if self.wait is not None:
            return BrowserActionPlan(
                action_type="wait",
                reason=reason,
                seconds=self.wait.seconds,
            )
        if self.go_back is not None:
            return BrowserActionPlan(
                action_type="go_back",
                reason=reason,
            )
        if self.extract is not None:
            return BrowserActionPlan(
                action_type="extract",
                reason=reason,
                query=self.extract.query,
                extract_links=self.extract.extract_links,
                start_from_char=self.extract.start_from_char,
            )
        if self.search_page is not None:
            return BrowserActionPlan(
                action_type="search_page",
                reason=reason,
                pattern=self.search_page.pattern,
            )
        if self.find_elements is not None:
            return BrowserActionPlan(
                action_type="find_elements",
                reason=reason,
                selector=self.find_elements.selector,
                attributes=self.find_elements.attributes,
                include_text=self.find_elements.include_text,
            )
        if self.switch_tab is not None:
            return BrowserActionPlan(
                action_type="switch_tab",
                reason=reason,
                tab_id=self.switch_tab.tab_id,
            )
        if self.close_tab is not None:
            return BrowserActionPlan(
                action_type="close_tab",
                reason=reason,
                tab_id=self.close_tab.tab_id,
            )
        if self.send_keys is not None:
            return BrowserActionPlan(
                action_type="send_keys",
                reason=reason,
                keys=self.send_keys.keys,
            )
        if self.read_content is not None:
            return BrowserActionPlan(
                action_type="read_content",
                reason=reason,
                goal=self.read_content.goal,
                source=self.read_content.source,
                context=self.read_content.context,
            )
        if self.get_dropdown_options is not None:
            return BrowserActionPlan(
                action_type="get_dropdown_options",
                reason=reason,
                index=self.get_dropdown_options.index,
            )
        if self.select_dropdown_option is not None:
            return BrowserActionPlan(
                action_type="select_dropdown_option",
                reason=reason,
                index=self.select_dropdown_option.index,
                text=self.select_dropdown_option.text,
            )
        if self.screenshot is not None:
            return BrowserActionPlan(
                action_type="screenshot",
                reason=reason,
                file_name=self.screenshot.file_name,
            )
        if self.save_as_pdf is not None:
            return BrowserActionPlan(
                action_type="save_as_pdf",
                reason=reason,
                file_name=self.save_as_pdf.file_name,
                print_background=self.save_as_pdf.print_background,
                landscape=self.save_as_pdf.landscape,
                scale=self.save_as_pdf.scale,
                paper_format=self.save_as_pdf.paper_format,
            )
        if self.done is not None:
            return BrowserActionPlan(
                action_type="done",
                reason=reason,
                final_response=self.done.text,
            )
        raise ValueError("Unsupported planner action.")


class BrowserPlannerOutput(BaseModel):
    evaluation_previous_goal: str = Field(min_length=1)
    memory: str = Field(min_length=1)
    next_goal: str = Field(min_length=1)
    action: list[BrowserPlannerAction] = Field(min_length=1)


class BrowserObservation(BaseModel):
    """Serializable browser observation used inside graph state."""

    url: str
    title: str
    tabs: list[dict]
    interactive_count: int
    llm_representation: str
    selector_preview: list[dict]
    recent_events: str | None = None


class BrowserActionResultModel(BaseModel):
    """Serializable wrapper around a browser runtime action result."""

    success: bool
    action_type: BrowserActionType
    extracted_content: str = ""
    error: str | None = None
    metadata: dict | None = None
    attachments: list[str] | None = None
    images: list[dict] | None = None


class BrowserStepRecord(BaseModel):
    """Minimal per-step execution record for API responses and logs."""

    step_number: int
    action: BrowserActionPlan
    result: BrowserActionResultModel | None = None


class BrowserTaskResult(BaseModel):
    """Final result returned by the explicit browser task entrypoint."""

    status: BrowserRunStatus
    final_response: str | None = None
    error_message: str | None = None
    current_url: str | None = None
    page_title: str | None = None
    step_count: int = 0
    steps: list[BrowserStepRecord] = Field(default_factory=list)
