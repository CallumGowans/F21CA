import tkinter as tk
from PIL import Image, ImageTk
from Agent import MovieAgent
import traceback

class GUI:
    def __init__(self):
        
        self.root = tk.Tk()
        print("Debug - Tk root created")
        self.root.geometry("500x500")
        self.root.title("Movie Recommender")
        
        self.muted = True

        self.open_mic_image = Image.open("images/microphone.png")
        self.open_mic_image.thumbnail((40, 40))
        self.open_mic_image_tk = ImageTk.PhotoImage(self.open_mic_image)
        self.closed_mic_image = Image.open("images/mute.png")
        self.closed_mic_image.thumbnail((40, 40))
        self.closed_mic_image_tk = ImageTk.PhotoImage(self.closed_mic_image)

        self.label = tk.Label(self.root, text="Please input your query", font=('Arial', 18))
        self.label.pack(padx=20, pady=20)
        print("Debug - Label packed")

        self.textbox = tk.Text(self.root, height=3, font=('Arial', 16))
        self.textbox.pack(padx=20, pady=5)
        print("Debug - Textbox packed")

        self.buttonframe = tk.Frame(self.root)
        self.buttonframe.columnconfigure(0, weight=1)
        self.buttonframe.columnconfigure(1, weight=1)
        self.buttonframe.columnconfigure(2, weight=1)

        self.submit_btn = tk.Button(self.buttonframe, text="Submit", font=('Arial', 14), command=self.text_request)
        self.submit_btn.grid(row=0, column=0, padx=10, pady=10)

        self.voice_btn = tk.Button(self.buttonframe, image=self.open_mic_image_tk, font=('Arial', 14), command=self.toggle_voice_control)
        self.voice_btn.grid(row=0, column=2, padx=10, pady=10)

        self.reset_btn = tk.Button(self.buttonframe, text="Reset", font=('Arial', 14), command=self.reset)
        self.reset_btn.grid(row=0, column=1, padx=10, pady=10)

        self.buttonframe.pack(pady=5, fill="x")
        print("Debug - Button frame packed")

        self.text_display = tk.Text(self.root, font=('Arial', 14), height=10, state='disabled')
        self.text_display.pack(padx=20, pady=5, fill="both", expand=True)
        print("Debug - Text display packed")

        self.text_display.tag_configure("user_input", background="lightblue", foreground="black")
        self.text_display.tag_configure("response", background="lightgreen", foreground="black")

        self.movie_agent = MovieAgent()

        print("Debug - Starting mainloop")
        self.root.mainloop()

    def show_response(self, message):
        response = self.movie_agent.agent_execute(message)
        self.text_display.insert(tk.END, f"Response: {response}\n", "response")

    def send_message(self, message):
        print(f"Debug - Message to display: '{message}'")
        self.text_display.config(state='normal')
        self.text_display.insert(tk.END, f"User: {message}\n", "user_input")
        self.textbox.delete("1.0", tk.END)
        self.text_display.config(state='disabled')
        self.root.update()

    def show_response(self, message):
        response = self.movie_agent.agent_execute(message)
        self.text_display.config(state='normal')
        self.text_display.insert(tk.END, f"Response: {response}\n", "response")
        self.text_display.config(state='disabled')
        self.root.update()

    def reset(self):
        self.textbox.delete("1.0", tk.END)
        self.text_display.config(state='normal')
        self.text_display.delete("1.0", tk.END)
        self.text_display.config(state='disabled')
        self.root.update()

    def toggle_voice_control(self):
        if self.muted:
            self.voice_btn.config(image=self.open_mic_image_tk)
            print("Microphone Muted - Stopped Listening")
            self.submit_btn.config(state='normal')
            self.textbox.config(state='normal')
            self.muted = False
        else:
            self.voice_btn.config(image=self.closed_mic_image_tk)
            print("Microphone Unmuted - Listening...")
            self.submit_btn.config(state='disabled')
            self.textbox.config(state='disabled')
            self.muted = True
            self.listen_and_display()

    def listen_and_display(self):
     
        user_input = agent.recognize_speech()
        self.send_message(user_input)
        self.show_response(user_input)

        if user_input:
            self.send_message(user_input)
            

    def text_request(self):
        user_input = self.textbox.get("1.0", "end").strip()
        self.send_message(user_input)
        self.show_response(user_input)
        

if __name__ == "__main__":
    GUI()