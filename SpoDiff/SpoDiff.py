#FusionAPI_python addin
#Author-kantoku
#Description-

import traceback
import adsk.core as core
import adsk.fusion as fusion 

from .SpotDifferenceFactory import SpotDifferenceFactory

_app = core.Application.cast(None)
_ui  = core.UserInterface.cast(None)
_handlers = []

# コマンド情報
_cmdInfo = {
    "id": "kantoku_3d_spot_diff",
    "name": "スポディフ",
    "tooltip": "3D間違い探しを解くよ!",
    "resources": "resources",
    "WorkSpaceId": "FusionSolidEnvironment",
    "panelId": "InspectPanel",
}

_selBodiesIpt: core.SelectionCommandInput = None
_txtBodiesInfo: core.TextBoxCommandInput = None
_previewIpt: core.BoolValueCommandInput = None
_spotFact: SpotDifferenceFactory = None


def run(context):
    ui = None
    try:
        global _app, _ui
        _app = core.Application.get()
        _ui = _app.userInterface

        # 今利用出来る全てのコマンドを取得
        cmdDefs: core.CommandDefinitions = _ui.commandDefinitions

        # 既に同一のIDのコマンドが無いか？
        global _cmdInfo
        cmdDef: core.CommandDefinition = cmdDefs.itemById(
            _cmdInfo["id"]
        )
        if cmdDef:
            # 見つけたら非情にも消し去る（行儀悪いから良い子はしない）
            cmdDef.deleteMe()

        # commandDefinitionを作る
        cmdDef = cmdDefs.addButtonDefinition(
            _cmdInfo["id"],
            _cmdInfo["name"],
            _cmdInfo["tooltip"],
            _cmdInfo["resources"],
        )

        # コマンドクリエイトイベント
        global _handlers
        onCommandCreated = CommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        # コントロール作成
        targetWorkSpace: core.Workspace = _ui.workspaces.itemById(
            _cmdInfo["WorkSpaceId"]
        )

        targetPanel: core.ToolbarPanel = targetWorkSpace.toolbarPanels.itemById(
            _cmdInfo["panelId"]
        )

        # コマンドをパネルに登録
        cmdControl :core.ToolbarPanel = targetPanel.controls.addCommand(
            cmdDef
        )

        cmdControl.isVisible = True

    except:
        if _ui:
            _ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class CommandCreatedHandler(core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: core.CommandCreatedEventArgs):
        try:
            cmd: core.Command = core.Command.cast(args.command)

            # event
            global _handlers
            onInputChanged = MyInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)

            onExecute = MyExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # inputs
            inputs: core.CommandInputs = cmd.commandInputs

            # inputs.addTextBoxCommandInput(
            #     "txtId",
            #     "",
            #     "違いを調べたいボディを２個選んでね",
            #     1,
            #     True,
            # )

            global _selBodiesIpt
            _selBodiesIpt = inputs.addSelectionInput(
                "_selBodiesIptId",
                "ボディ",
                "２個のボディを選択してね",
            )
            _selBodiesIpt.addSelectionFilter(core.SelectionCommandInput.Bodies)
            _selBodiesIpt.setSelectionLimits(2,2)

            global _previewIpt
            _previewIpt = inputs.addBoolValueInput(
                "previewIptId",
                "確認",
                False,
                _cmdInfo["resources"],
                False,
            )
            _previewIpt.isEnabled = False

            global _txtBodiesInfo
            _txtBodiesInfo = inputs.addTextBoxCommandInput(
                "_selBodiesIptId",
                "情報",
                "-",
                3,
                True,
            )

        except:
            if _ui:
                _ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


class MyExecuteHandler(core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: core.CommandEventArgs):
        global _spotFact
        if not _spotFact: return

        _spotFact.create_diff_faces()


class MyInputChangedHandler(core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: core.InputChangedEventArgs):
        global _selBodiesIpt
        global _txtBodiesInfo
        global _previewIpt
        global _spotFact

        if args.input == _selBodiesIpt:
            if not _selBodiesIpt.selectionCount == 2:
                _txtBodiesInfo.text = "-"

                _previewIpt.isEnabled = False
            else:
                _spotFact = SpotDifferenceFactory(
                    _selBodiesIpt.selection(0).entity,
                    _selBodiesIpt.selection(1).entity,
                )
                _txtBodiesInfo.text = _spotFact.get_bodies_info()

                _previewIpt.isEnabled = True

        if args.input == _previewIpt:
            _txtBodiesInfo.text = _spotFact.get_diff_info()
        #     if not _selBodiesIpt.selectionCount == 2:
        #         _txtBodiesInfo.text = "-"
        #     else:
        #         global _spotFact
        #         _spotFact = SpotDifferenceFactory(
        #             _selBodiesIpt.selection(0).entity,
        #             _selBodiesIpt.selection(1).entity,
        #         )
        #         _txtBodiesInfo.text = _spotFact.get_bodies_info()


def stop(context):
    try:
        # コマンド実行中であれば終了する
        if not _ui.activeCommand == "SelectCommand":
            _app.executeTextCommand(u"Commands.Start  SelectCommand")

        # コントロール削除
        global _cmdInfo
        targetWorkSpace: core.Workspace = _ui.workspaces.itemById(
            _cmdInfo["WorkSpaceId"]
        )

        targetPanel: core.ToolbarPanel = targetWorkSpace.toolbarPanels.itemById(
            _cmdInfo["panelId"]
        )

        cmdControl :core.ToolbarPanel = targetPanel.controls.itemById(
            _cmdInfo["id"]
        )

        cmdControl.deleteMe()

        # コマンドcmdDefを削除
        cmdDef :core.CommandDefinition = _ui.commandDefinitions.itemById(
            _cmdInfo["id"]
        )
        if cmdDef:
            cmdDef.deleteMe()

    except:
        print("Failed:\n{}".format(traceback.format_exc()))