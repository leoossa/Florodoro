import argparse
import os
import sys
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from math import sin, pi, acos, degrees
from random import random, uniform, choice, randint

from PyQt5.QtCore import QTimer, QTime, Qt, QDate, QDir, QUrl, QPointF, QSize, QRect, QRectF
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QIcon, QPainterPath, QKeyEvent
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox, QAction, QSizePolicy, \
    QMessageBox, QMenuBar, QStackedLayout
from PyQt5.QtWidgets import QVBoxLayout, QLabel

from plyer import notification


def smoothen_curve(x: float):
    """f(x) with a smoother beginning and end."""
    # TODO: move to utilities?
    return (sin((x - 1 / 2) * pi) + 1) / 2


class Drawable(ABC):
    """Something that has a draw function that takes a painter to be painted. Also contains some convenience methods
    for drawing the thing and saving it to an SVG."""

    @abstractmethod
    def draw(self, painter: QPainter, width: int, height: int):
        """Draw the drawable onto a painter, given its size."""
        pass

    def save(self, path: str, width: int, height: int):
        """Save the drawable to the specified file, given its size."""
        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRect(0, 0, width, height))

        painter = QPainter(generator)
        self.draw(painter, width, height)
        painter.end()


class Plant(Drawable):
    age = 0  # every plant has a current age (from 0 to 1)
    maxAge = None  # and a max age (from 0 to 1)

    green_color = QColor(0, 119, 0)
    white_color = QColor(255, 255, 255)

    def set_current_age(self, age: float):
        """Set the current age of the plant (normalized from 0 to 1). Changes the way it is drawn."""
        self.age = age

    def set_max_age(self, maxAge: float):
        """Change the plant's max age, re-generating it in the process."""
        self.maxAge = maxAge
        self.generate()

    def get_adjusted_age(self):
        """Return the age, adjusted to increase to 1 slower (some parts of the plant grow slower than others)."""
        return self.age ** 2

    def draw(self, painter: QPainter, width: int, height: int):
        if self.maxAge is None:
            return

        w = min(width, height)
        h = min(width, height)

        # position to the bottom center of the canvas
        painter.translate(width / 2, height)
        painter.scale(1, -1)

        self._draw(painter, w, h)

    def generate(self):
        # so we don't go from 0 to 1, but from 0.5 to 1
        # a coefficient to multiply all parts of the given plant by that depend on its maximum age
        self.age_coefficient = (self.maxAge + 1) / 2

        # make the sizes somewhat random and organic
        self.deficit_coefficient = uniform(0.9, 1)


class Flower(Plant):

    def generateLeafs(self, count):
        # position / size coefficient (smaller/larger leafs) / rotation
        self.leafs = [(uniform(self.deficit_coefficient * 0.25, self.deficit_coefficient * 0.40), uniform(0.9, 1.1),
                       (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1))) for i in
                      range(count)]

    def generate(self):
        super().generate()

        # the ending position of the flower
        x_coefficient = uniform(0.4, 1) * (-1 if random() < 0.5 else 1)
        self.x_position = lambda width: width / 9 * x_coefficient
        self.y_position = lambda height: height / 2.5 * self.deficit_coefficient * self.age_coefficient

        # the size of the leafs
        self.leaf_size = lambda width: width / 7 * self.deficit_coefficient * self.age_coefficient

        # always generate 2 leafs
        self.generateLeafs(2)

        # the width of the stem
        self.stem_width = uniform(3.5, 4) * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        self.x = self.x_position(width) * smoothen_curve(self.age)
        self.y = self.y_position(height) * smoothen_curve(self.age)

        painter.setPen(QPen(self.green_color, self.stem_width * smoothen_curve(self.age)))

        # draw the stem
        path = QPainterPath()
        path.quadTo(0, self.y * 0.6, self.x, self.y)
        painter.drawPath(path)

        # draw the leaves
        for position, coefficient, rotation in self.leafs:
            painter.save()

            # find the point on the stem and rotate the leaf accordingly
            painter.translate(path.pointAtPercent(position))
            painter.rotate(degrees(rotation))

            # rotate according to where the flower is leaning towards
            if self.y != 0:
                painter.rotate(-degrees(sin(self.x / self.y)))

            # make it so both leaves are facing the same direction
            if rotation < 0:
                painter.scale(-1, 1)

            painter.setBrush(QBrush(self.green_color))
            painter.setPen(QPen(0))

            # draw the leaf
            leaf = QPainterPath()
            leaf.setFillRule(Qt.WindingFill)
            ls = self.leaf_size(width) * smoothen_curve(self.age) ** 2 * coefficient
            leaf.quadTo(0.4 * ls, 0.5 * ls, 0, ls)
            leaf.cubicTo(0, 0.5 * ls, -0.4 * ls, 0.4 * ls, 0, 0)
            painter.drawPath(leaf)

            painter.restore()


class CircularFlower(Flower):
    # colors of the Florodoro logo
    colors = [
        QColor(139, 139, 255),  # blue-ish
        QColor(72, 178, 173),  # green-ish
        QColor(255, 85, 85),  # red-ish
        QColor(238, 168, 43),  # orange-ish
        QColor(226, 104, 155),  # pink-ish
    ]

    def triangle_pellet(self, painter: QPainter, pellet_size):
        """A pellet that is pointy and triangular (1st in logo)"""
        pellet_size *= 1.5

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)
        pellet.quadTo(0.9 * pellet_size, 0.5 * pellet_size, 0, pellet_size)
        pellet.quadTo(-0.5 * pellet_size, 0.4 * pellet_size, 0, 0)
        painter.drawPath(pellet)

    def circular_pellet(self, painter: QPainter, pellet_size):
        """A perfectly circular pellet (2nd in logo)."""
        painter.drawEllipse(QRectF(0, 0, pellet_size, pellet_size))

    def round_pellet(self, painter: QPainter, pellet_size):
        """A pellet that is round but not a circle (3rd in the logo)."""
        pellet_size *= 1.3

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)

        for c in [1, -1]:
            pellet.quadTo(c * pellet_size * 0.8, pellet_size * 0.9, 0, pellet_size if c != -1 else 0)

        painter.drawPath(pellet)

    def dip_pellet(self, painter: QPainter, pellet_size):
        """A pellet that has a dip in the middle (4th in the logo)."""
        pellet_size *= 1.2

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)

        for c in [1, -1]:
            pellet.quadTo(c * pellet_size, pellet_size * 1.4, 0, pellet_size if c != -1 else 0)

        painter.drawPath(pellet)

    def generate(self):
        super().generate()

        # color of the flower
        self.color = choice(self.colors)

        self.number_of_pellets = randint(5, 7)

        self.pellet_size = lambda width: width / 9 * self.deficit_coefficient * self.age_coefficient

        # the center of the plant is smaller, compared to other pellet sizes
        self.center_pellet_smaller_coefficient = uniform(0.75, 0.85)

        self.pellet_drawing_function = choice(
            [self.circular_pellet, self.triangle_pellet, self.dip_pellet, self.round_pellet])

        # the m and n pellets don't look good with any other number of leafs (other than 5)
        if self.pellet_drawing_function in [self.dip_pellet, self.round_pellet]:
            self.number_of_pellets = 5

    def _draw(self, painter: QPainter, width: int, height: int):
        super()._draw(painter, width, height)

        painter.save()

        # move to the position of the flower
        painter.translate(self.x, self.y)

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.color))

        pellet_size = self.pellet_size(width) * smoothen_curve(self.age)

        # draw each of the pellets
        for i in range(self.number_of_pellets):
            self.pellet_drawing_function(painter, pellet_size)
            painter.rotate(360 / self.number_of_pellets)

        # the center of the flower
        painter.setBrush(QBrush(self.white_color))
        pellet_size *= self.center_pellet_smaller_coefficient
        painter.drawEllipse(QRectF(-pellet_size / 2, -pellet_size / 2, pellet_size, pellet_size))

        painter.restore()


class Tree(Plant):
    """A simple tree class that all trees originate from."""
    brown_color = QColor(77, 51, 0)

    def generateBranches(self, count):
        # positions of branches up the tree, + their orientations (where they're turned towards)
        self.branches = [(uniform(self.deficit_coefficient * 0.45, self.deficit_coefficient * 0.55),
                          (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1)) * acos(
                              uniform(0.4, 0.6))) for i in
                         range(count)]

    def generate(self):
        super().generate()

        # generate somewhere between 1 and 2 branches
        self.generateBranches(round(uniform(1, 2 * self.age_coefficient)))

        # the width/height of the main branch
        self.base_width = lambda width: width / 15 * self.deficit_coefficient * self.age_coefficient
        self.base_height = lambda height: height / 1.7 * self.deficit_coefficient * self.age_coefficient

        # the width/height of the other branches
        self.branch_width = lambda width: width / 18 * self.deficit_coefficient * self.age_coefficient
        self.branch_height = lambda height: height / 2.7 * self.deficit_coefficient * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setBrush(QBrush(self.brown_color))

        # main branch
        painter.drawPolygon(QPointF(-self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(0, self.base_height(height) * smoothen_curve(self.age)))

        # other branches
        for h, rotation in self.branches:
            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            painter.drawPolygon(
                QPointF(-self.branch_width(width) * smoothen_curve(self.get_adjusted_age()) * (1 - h), 0),
                QPointF(self.branch_width(width) * smoothen_curve(self.get_adjusted_age()) * (1 - h), 0),
                QPointF(0, self.branch_height(height) * smoothen_curve(self.get_adjusted_age()) * (1 - h)))

            painter.restore()


class OrangeTree(Tree):
    orange_color = QColor(243, 148, 30)

    def generate(self):
        super().generate()

        # orange trees will always have 2 branches
        # it just looks better
        self.generateBranches(2)

        # the size (percentage of width/height) + the position of the circle on the branch
        # the last one is the main ellipse
        self.branch_circles = [(uniform(self.deficit_coefficient * 0.30, self.deficit_coefficient * 0.37),
                                uniform(self.deficit_coefficient * 0.9, self.deficit_coefficient)) for _ in
                               range(len(self.branches) + 1)]

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.orange_color))

        for i, branch in enumerate(self.branches):
            h, rotation = branch

            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            top_of_branch = self.branch_height(height) * smoothen_curve(self.get_adjusted_age()) * (1 - h)
            circle_on_branch_position = top_of_branch * self.branch_circles[i][1]

            r = ((width + height) / 2) * self.branch_circles[i][0] * smoothen_curve(self.get_adjusted_age()) * (
                    1 - h) * self.age_coefficient

            painter.setBrush(QBrush(self.orange_color))
            painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

            painter.restore()

        top_of_branch = self.base_height(height) * smoothen_curve(self.age)
        circle_on_branch_position = top_of_branch * self.branch_circles[-1][1]

        # make the main ellipse slightly larger
        increase_size = 1.3
        r = ((width + height) / 2) * self.branch_circles[-1][0] * smoothen_curve(self.get_adjusted_age()) * (
                1 - h) * self.age_coefficient * increase_size

        painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

        super()._draw(painter, width, height)


class GreenTree(Tree):
    def generate(self):
        super().generate()

        self.green_width = lambda width: width / 3.2 * self.deficit_coefficient * self.age_coefficient
        self.green_height = lambda height: height / 1.5 * self.deficit_coefficient * self.age_coefficient

        self.offset = lambda height: min(height * .95, self.base_height(height * 0.3 * smoothen_curve(self.age)))

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.green_color))

        painter.drawPolygon(QPointF(-self.green_width(width) * smoothen_curve(self.age), self.offset(height)),
                            QPointF(self.green_width(width) * smoothen_curve(self.age), self.offset(height)),
                            QPointF(0, self.green_height(height) * smoothen_curve(self.age) + self.offset(height)))

        super()._draw(painter, width, height)


class DoubleGreenTree(GreenTree):

    def generate(self):
        super().generate()

        self.second_green_width = lambda width: width / 3.5 * self.deficit_coefficient * self.age_coefficient
        self.second_green_height = lambda height: height / 2.4 * self.deficit_coefficient * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.green_color))

        offset = self.base_height(height * 0.3 * smoothen_curve(self.age))
        second_offset = (self.green_height(height) - self.second_green_height(height)) * smoothen_curve(self.age)

        painter.drawPolygon(
            QPointF(-self.second_green_width(width) * smoothen_curve(self.age) ** 2, offset + second_offset),
            QPointF(self.second_green_width(width) * smoothen_curve(self.age) ** 2, offset + second_offset),
            QPointF(0, min(
                self.second_green_height(height) * smoothen_curve(self.age) + offset + second_offset,
                height * 0.95)))

        super()._draw(painter, width, height)


class Canvas(QWidget):
    """A widget that takes a drawable object and constantly draws it."""

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        self.object = None

    def save(self, path: str):
        """Save the drawable object to the specified file."""
        self.object.save(path, self.width(), self.height())

    def set_drawable(self, obj: Drawable):
        """Set the drawable that the canvas draws."""
        self.object = obj

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setClipRect(0, 0, self.width(), self.height())

        if self.object is None:
            return

        # draw the drawable
        painter.save()
        self.object.draw(painter, self.width(), self.height())
        painter.restore()

        painter.end()


class Florodoro(QWidget):

    def parseArguments(self):
        parser = argparse.ArgumentParser(
            description="A pomodoro timer that grows procedurally generated trees and flowers while you're studying.",
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="run the app in debug mode",
        )

        return parser.parse_args()

    def __init__(self):
        super().__init__()

        arguments = self.parseArguments()

        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        self.WIDTH = 500
        self.HEIGHT = 500

        self.ROOT_FOLDER = "~/.florodoro/"

        self.SOUNDS_FOLDER = "sounds/"
        self.PLANTS_FOLDER = "plants/"
        self.IMAGE_FOLDER = "images/"

        self.PLANTS = [GreenTree, DoubleGreenTree, OrangeTree, CircularFlower]

        self.DEBUG = arguments.debug

        self.DEFAULT_STUDY_TIME = 45
        self.DEFAULT_BREAK_TIME = 15

        self.MAX_PLANT_AGE = 90  # maximum number of minutes to make the plant optimal in size

        self.WIDGET_SPACING = 10

        self.MAX_TIME = 180
        self.STEP = 5

        self.INITIAL_TEXT = "Start!"

        self.STUDY_TEXT = "Study"
        self.BREAK_TEXT = "Break"
        self.RESET_TEXT = "Reset"

        self.PAUSE_TEXT = "Pause"
        self.CONTINUE_TEXT = "Continue"

        self.BREAK_COLOR = "#B37700"
        self.DISABLED_BREAK_COLOR = "#FFBD7F"

        self.menuBar = QMenuBar(self)
        self.options_menu = self.menuBar.addMenu('Options')

        self.notify_menu = self.options_menu.addMenu("&Notify")

        self.sound_action = QAction("&Sound", self, checkable=True, checked=True)
        self.notify_menu.addAction(self.sound_action)

        self.popup_action = QAction("&Pop-up", self, checkable=True, checked=True)
        self.notify_menu.addAction(self.popup_action)

        if self.DEBUG:
            self.sound_action.setChecked(False)

        self.menuBar.addAction(
            QAction(
                "&About",
                self,
                triggered=lambda: QMessageBox.information(
                    self,
                    "About",
                    "This application was created by Tomáš Sláma. It is heavily inspired by the Android app Forest, "
                    "but with all of the plants generated procedurally. It's <a href='https://github.com/xiaoxiae/Florodoro'>open source</a> and licensed "
                    "under MIT, so do as you please with the code and anything else related to the project.",
                ),
            )
        )

        self.plant_menu = self.options_menu.addMenu("&Plants")

        self.plant_images = []
        self.plant_checkboxes = []

        for plant in self.PLANTS:
            self.plant_images.append(tempfile.NamedTemporaryFile(suffix=".svg"))
            tmp = plant()
            tmp.set_max_age(1)
            tmp.set_current_age(1)
            tmp.generate()
            tmp.save(self.plant_images[-1].name, 200, 200)

            action = QAction(
                self,
                icon=QIcon(self.plant_images[-1].name),
                checkable=True,
                checked=True,
            )

            self.plant_menu.addAction(action)
            self.plant_checkboxes.append(action)

        # there there is currently a plant that is being grown
        # initially False; note that pressing start doesn't set this to true if all plants are deselected!
        self.plant_growing = False

        self.menuBar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        main_vertical_layout = QVBoxLayout(self)
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        main_vertical_layout.setSpacing(0)
        main_vertical_layout.addWidget(self.menuBar)

        self.canvas = Canvas(self)

        font = self.font()
        font.setPointSize(100)

        self.main_label = QLabel(self)
        self.main_label.setFont(font)
        self.main_label.setText(self.INITIAL_TEXT)

        font.setPointSize(26)
        self.cycle_label = QLabel(self)
        self.cycle_label.setAlignment(Qt.AlignTop)
        self.cycle_label.setMargin(20)
        self.cycle_label.setFont(font)

        main_horizontal_layout = QHBoxLayout(self)

        self.study_time_spinbox = QSpinBox(self, prefix="Study for: ", suffix="min.", minimum=1, maximum=self.MAX_TIME,
                                           value=self.DEFAULT_STUDY_TIME,
                                           singleStep=self.STEP)
        self.break_time_spinbox = QSpinBox(self, prefix="Rest for: ", suffix="min.", minimum=1, maximum=self.MAX_TIME,
                                           value=self.DEFAULT_BREAK_TIME,
                                           singleStep=self.STEP)
        self.cycles_spinbox = QSpinBox(self, prefix="Cycles: ", minimum=1, value=1)

        # keep track of remaning number of cycles and the starting number of cycles
        self.cycles = self.cycles_spinbox.value()
        self.initial_cycles = self.cycles

        stacked_layout = QStackedLayout(self)
        stacked_layout.addWidget(self.main_label)
        stacked_layout.addWidget(self.cycle_label)
        stacked_layout.addWidget(self.canvas)
        stacked_layout.setStackingMode(QStackedLayout.StackAll)

        self.main_label.setAlignment(Qt.AlignCenter)

        main_vertical_layout.addLayout(stacked_layout)

        self.break_time_spinbox.setStyleSheet(f'color:{self.BREAK_COLOR};')

        self.study_button = QPushButton(self, text=self.STUDY_TEXT, clicked=self.start)
        self.break_button = QPushButton(self, text=self.BREAK_TEXT, clicked=self.start_break)
        self.break_button.setStyleSheet(f"QPushButton:disabled{{ color: {self.DISABLED_BREAK_COLOR} }} QPushButton:enabled{{ color: {self.BREAK_COLOR} }}")

        self.pause_button = QPushButton(self, text=self.PAUSE_TEXT, clicked=self.toggle_pause)
        self.reset_button = QPushButton(self, text=self.RESET_TEXT, clicked=self.press_reset)

        main_horizontal_layout.addWidget(self.study_time_spinbox)
        main_horizontal_layout.addWidget(self.break_time_spinbox)
        main_horizontal_layout.addWidget(self.cycles_spinbox)
        main_horizontal_layout.addWidget(self.study_button)
        main_horizontal_layout.addWidget(self.break_button)
        main_horizontal_layout.addWidget(self.pause_button)
        main_horizontal_layout.addWidget(self.reset_button)

        main_vertical_layout.addLayout(main_horizontal_layout)

        self.setLayout(main_vertical_layout)

        self.study_timer = QTimer(self)
        self.study_timer.timeout.connect(self.decrease_remaining_time)
        self.study_timer_frequency = 1 / 60 * 1000
        self.study_timer.setInterval(int(self.study_timer_frequency))

        self.player = QMediaPlayer(self)

        self.setWindowIcon(QIcon(self.IMAGE_FOLDER + "icon.svg"))
        self.setWindowTitle("Florodoro")

        # set initial UI state
        self.reset()

        self.show()

    def start_break(self):
        """Starts the break, instead of the study."""
        self.start(do_break=True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Debug-related keyboard controls."""
        if self.DEBUG:
            if event.key() == Qt.Key_Escape:
                possible_plants = [plant for i, plant in enumerate(self.PLANTS) if self.plant_checkboxes[i].isChecked()]

                if len(possible_plants) != 0:
                    self.plant = choice(possible_plants)()
                    self.canvas.set_drawable(self.plant)
                    self.plant.set_max_age(1)
                    self.plant.set_current_age(1)
                    self.canvas.update()

    def start(self, do_break=False, cycled_call=False):
        """The function for starting either the study or break timer (depending on do_break)."""
        self.study_button.setDisabled(not do_break)
        self.break_button.setDisabled(True)
        self.reset_button.setDisabled(False)

        self.pause_button.setDisabled(False)
        self.pause_button.setText(self.PAUSE_TEXT)

        # study_done is set depending on whether we finished studying (are having a break) or not
        self.study_done = do_break

        if not cycled_call and not do_break:
            self.cycles = self.cycles_spinbox.value()
            self.initial_cycles = self.cycles

        self.main_label.setStyleSheet('' if not do_break else f'color:{self.BREAK_COLOR};')

        # the total time to study for (spinboxes are minutes)
        # since it's rounded down and it looks better to start at the exact time, 0.99 is added
        self.total_time = (self.study_time_spinbox if not do_break else self.break_time_spinbox).value() * 60 + 0.99
        self.ending_time = datetime.now() + timedelta(minutes=self.total_time / 60)

        # so it's displayed immediately
        self.update_time_label(self.total_time)
        self.update_cycles_label()

        # don't start showing canvas and growing the plant when we're not studying
        if not do_break:
            possible_plants = [plant for i, plant in enumerate(self.PLANTS) if self.plant_checkboxes[i].isChecked()]

            if len(possible_plants) != 0:
                self.plant = choice(possible_plants)()
                self.canvas.set_drawable(self.plant)
                self.plant.set_max_age(min(1, (self.total_time / 60) / self.MAX_PLANT_AGE))
                self.plant.set_current_age(0)
                self.plant_growing = True
            else:
                self.plant_growing = False

        self.study_timer.stop()  # it could be running - we could be currently in a break
        self.study_timer.start()

    def toggle_pause(self):
        # stop the timer, if it's running
        if self.study_timer.isActive():
            self.study_timer.stop()
            self.pause_button.setText(self.CONTINUE_TEXT)
            self.pause_time = datetime.now()

        # if not, resume
        else:
            self.ending_time += datetime.now() - self.pause_time
            self.study_timer.start()
            self.pause_button.setText(self.PAUSE_TEXT)

    def press_reset(self):
        """For some reason, pressing a button calls reset() with button_press being false."""
        self.reset(button_press=True)

    def reset(self, button_press=True):
        self.study_timer.stop()
        self.pause_button.setText(self.PAUSE_TEXT)

        self.main_label.setStyleSheet('')
        self.study_button.setDisabled(False)
        self.break_button.setDisabled(False)
        self.pause_button.setDisabled(True)
        self.reset_button.setDisabled(True)

        if self.plant_growing:
            self.plant.set_current_age(0)

        # pressing study > reset > break with cycles > 2 continues doing the cycles after end of break
        # this prevents that
        if button_press:
            self.cycles = 1

        self.main_label.setText(self.INITIAL_TEXT)
        self.cycle_label.setText('')

    def update_time_label(self, time):
        """Update the text of the time label, given some time in seconds."""
        hours = int(time // 3600)
        minutes = int((time // 60) % 60)
        seconds = int(time % 60)

        # smooth timer: hide minutes/hours if there are none
        result = ""
        if hours == 0:
            if minutes == 0:
                result += str(seconds)
            else:
                result += str(minutes) + QTime(0, 0, seconds).toString(":ss")
        else:
            result += str(hours) + QTime(0, minutes, seconds).toString(":mm:ss")

        self.main_label.setText(result)

    def play_sound(self, name: str):
        """Play a file from the sound directory. Extension is not included, will be added automatically."""
        for file in os.listdir(self.SOUNDS_FOLDER):
            # if the file starts with the provided name and only contains an extension after, try to play it
            if file.startswith(name) and file[len(name):][0] == ".":
                path = QDir.current().absoluteFilePath(self.SOUNDS_FOLDER + file)
                url = QUrl.fromLocalFile(path)
                content = QMediaContent(url)
                self.player.setMedia(content)
                self.player.play()

    def show_notification(self, message: str):
        """Show the specified notification using plyer."""
        notification.notify("Florodoro", message, "Florodoro", os.path.abspath(self.IMAGE_FOLDER + "icon.svg"))

    def update_cycles_label(self):
        if self.initial_cycles != 1 and not self.study_done:
            self.cycle_label.setText(f"{self.initial_cycles - self.cycles + 1}/{self.initial_cycles}")

    def decrease_remaining_time(self):
        """Decrease the remaining time by the timer frequency. Updates clock/plant growth."""
        if self.DEBUG:
            self.ending_time -= timedelta(seconds=30)

        time_delta = self.ending_time - datetime.now()
        leftover_time = time_delta.total_seconds()

        self.update_time_label(leftover_time)

        if leftover_time <= 0:
            if self.study_done:
                self.reset(button_press=False)

                if self.sound_action.isChecked():
                    self.play_sound("break_done")

                if self.popup_action.isChecked():
                    self.show_notification("Break is over!")

                if self.cycles != 1:
                    self.cycles -= 1
                    self.start(cycled_call=True)

                    self.update_cycles_label()
                else:
                    self.cycle_label.setText('')
            else:
                self.start_break()

                name = QDate.currentDate().toString(Qt.ISODate) + "|" + QTime.currentTime().toString("hh:mm:ss")

                if self.DEBUG:
                    with open(os.path.expanduser(self.ROOT_FOLDER) + "florodoro.log", "a") as f:
                        f.write(name + " - finished studying for " + str(self.total_time // 60) + " minutes." + "\n")

                if self.plant_growing:
                    path = os.path.expanduser(self.ROOT_FOLDER) + self.PLANTS_FOLDER

                    if not os.path.exists(path):
                        os.makedirs(path)

                    self.canvas.save(path + name + ".svg")

                if self.sound_action.isChecked():
                    self.play_sound("study_done")

                if self.popup_action.isChecked():
                    self.show_notification("Studying finished, take a break!")
        else:
            # if there is leftover time and we haven't finished studying, grow the plant
            if not self.study_done:
                if self.plant_growing:
                    self.plant.set_current_age(1 - (leftover_time / self.total_time))

                self.canvas.update()


def run():
    app = QApplication(sys.argv)
    Florodoro()
    app.exit(app.exec_())


if __name__ == '__main__':
    run()
