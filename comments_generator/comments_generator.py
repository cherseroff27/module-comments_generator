import os
import time
import pyperclip
import subprocess
from selenium.webdriver import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from web_elements_handler import WebElementsHandler as Weh
from manual_script_control import ManualScriptControl


class CommentsGenerator:
    def __init__(self, driver, tg_notificator):
        self.driver = driver
        self.actions = ActionChains(self.driver)
        self.tg_notificator = tg_notificator


    def open_page(self, link):
        self.driver.get(link)


    def is_chatgpt_tab_open(self):
        original_window = self.driver.current_window_handle

        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)

            if "chatgpt.com" in self.driver.current_url:
                return True

        self.driver.switch_to.window(original_window)
        return False


    def open_new_tab(self, url):
        self.driver.execute_script(f"window.open('{url}', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])


    def get_into_chatgpt(self, chatgpt_link):
        if self.is_chatgpt_tab_open():
            self.driver.execute_script("location.reload()")
            self.countdown_sleep(5)
        else:
            self.open_new_tab(chatgpt_link)

        challenge_form_locator = "//form[@id='challenge-form']"
        successful_enter_locator1 = "//div[@class='grow']"
        successful_enter_locator2 = "//div[@class='relative inline-flex justify-center text-center text-2xl font-semibold leading-9']"
        must_refresh = False
        while True:
            self.check_if_popup_appears()

            if must_refresh:
                self.driver.execute_script("location.reload()")
                self.countdown_sleep(5)
                must_refresh = True

            try:
                element = Weh.wait_for_element_xpath(challenge_form_locator, successful_enter_locator1,
                                               successful_enter_locator2, driver=self.driver, timeout=3)
                if element is not None:
                    if element.get_attribute("class") == "grow" or element.get_attribute("class") == "relative inline-flex justify-center text-center text-2xl font-semibold leading-9":
                        print("Ура! Успешно вошел на страницу диалога с GhatGPT.")
                        break
                    elif element.get_attribute("id") == "challenge-form":
                        self.tg_notificator.send_telegram_message("Нужно вручную пройти проверку Cloudflare.\n" * 3)
                        ManualScriptControl.wait_for_user_input("Нужно вручную нажать на CloudFlare капчу.")
            except Exception as e:
                print("Ошибка: ", e)


    def get_comments(self, chatgpt_link, article_content, gender_flag, comments_amount):
        self.get_into_chatgpt(chatgpt_link)

        self.check_if_popup_appears()

        self.generate_comments(article_content, gender_flag, comments_amount)

        return self.fetch_generated_comments()


    def check_if_popup_appears(self):
        popup_element = None

        try:
            popup_locator_eng = "//a[contains(text(), 'Stay logged out')]"
            popup_locator_rus = "//a[contains(text(), 'Не входить')]"
            popup_element = Weh.wait_for_element_xpath(popup_locator_eng, popup_locator_rus
                                                 , driver=self.driver, timeout=5)
        except Exception as ex:
            print("Произошла ошибка в проверке появления всплывающего окна: ", ex)

        if popup_element is not None:
            Weh.move_to_element_and_click(self.actions, popup_element)
        else:
            print("Элемент 'Stay logged out' не возник.")


    def fetch_generated_comments(self):
        time.sleep(3)
        streaming_answer_locator = "//div[@class='result-streaming markdown prose w-full break-words dark:prose-invert light']"
        complete_answer_locator = "//div[@class='markdown prose w-full break-words dark:prose-invert light']"

        scroll_attempts = 0  # Считаем количество прокруток для предотвращения бесконечного цикла
        max_scroll_attempts = 10  # Максимальное число прокруток страни

        while scroll_attempts < max_scroll_attempts:
            try:
                element = Weh.wait_for_element_xpath(complete_answer_locator, streaming_answer_locator,
                                               driver=self.driver, timeout=3)   # Ищем нужный элемент

                if element:
                    if "result-streaming markdown" in element.get_attribute("class"):   # Проверяем, печатает ли ChatGPT или ответ завершен
                        self.driver.execute_script("arguments[0].scrollIntoView();", element)
                        time.sleep(3)
                        print("ChatGPT все еще печатает ответ...")
                    elif "markdown prose w-full" in element.get_attribute("class"):
                        self.driver.execute_script("arguments[0].scrollIntoView();", element)
                        time.sleep(3)
                        print("Получен полный ответ.")
                        break
            except Exception as ex:
                print(f"Ошибка при обработке элемента: {ex}")

            # Если элемент не найден, прокручиваем страницу вниз
            print("Элемент не найден, прокручиваем страницу...")
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(2)  # Даем время для загрузки нового контента после прокрутки
            scroll_attempts += 1

        if scroll_attempts == max_scroll_attempts:
            print("Достигнуто максимальное количество прокруток, элемент не найден.")

        li_elements_locator = "//div[@class='markdown prose w-full break-words dark:prose-invert light']//li"
        li_element = Weh.wait_for_element_xpath(li_elements_locator, driver=self.driver, timeout=30)
        if li_element is not None:
            li_elements = self.driver.find_elements(By.XPATH, li_elements_locator)
            generated_comments = [li.text for li in li_elements]
            return generated_comments
        else:
            print("Не нашел списка с комментариями :(")


    def generate_comments(self, article_content, gender_flag, comments_amount):
        input_field_locator = "//p[@class='placeholder']"
        input_field_element = Weh.wait_for_element_xpath(input_field_locator, driver=self.driver, timeout=30)

        if input_field_element:
            prompt_text = self.generate_prompt(gender_flag, comments_amount)

            result = subprocess.run([os.path.join(os.getcwd(), "KeyboardSwitcher.exe")], capture_output=True, text=True)
            print(result.stdout)

            pyperclip.copy(prompt_text)
            Weh.move_to_element_and_click(self.actions, input_field_element)
            self.countdown_sleep(1)
            input_field_element.send_keys(Keys.CONTROL, 'v')
            self.countdown_sleep(1)
            pyperclip.copy(article_content)
            self.countdown_sleep(1)
            input_field_element.send_keys(Keys.CONTROL, 'v')
            self.countdown_sleep(1)
            input_field_element.send_keys(Keys.RETURN)


    @staticmethod
    def generate_prompt(gender_flag, comments_amount):
        gender_pronoun = "мужского" if gender_flag == 1 else "женского"

        prompt_text = (
            f"Мне нужно, чтобы ты написал максимально развернутые комментарии для статьи:\n\n"
            f"Комментарии должны быть реалистичными, описывающими личностный опыт комментаторов,"
            f"как будто их написали реальные люди, разного возраста, со своими привычками в комментировании статей.\n"
            f"(Поддерживающие/Сравнительные/Философские/Юмористические/Эмоциональные/Информативные и т.д.)."
            f"Нужно, чтобы в 5 из 10 случаев допускались грамматические и лексические ошибки!"
            f"Важно, чтобы половина комментариев была написана так, как это написал бы не слишком грамотный"
            f"человек, со своими уникальными словами паразитами.\n\n"
            f"Важно! Комментарии нужно писать СТРОГО в указанном формате - сначала номер комментария, "
            f"точка, пробел, текст комментария без кавычек.\n"
            f"Приветствуется использование эмодзи (редко).\n"
            f"Пример (ответ должен быть в виде списка!):\n"
            f"1. текст комментария 1\n"
            f"2. текст комментария 2\n"
            f"3. текст комментария 3\n\n"
            f"НИЧЕГО КРОМЕ КОММЕНТАРИЕВ ПИСАТЬ НЕ НУЖНО! Никакого лишнего текста!\n\n"
            f"Количество комментариев - {comments_amount} (СТРОГО ТАКОЕ КОЛИЧЕСТВО!).\n"
            f"Учти, что нужно писать комментарии от лица {gender_pronoun} пола.\n\n"
        )

        return prompt_text


    @staticmethod
    def countdown_sleep(duration):
        for remaining in range(duration, 0, -1):
            print(f"\rОсталось спать {remaining} секунд", end="")
            time.sleep(1)
        print("\rСон завершен!")