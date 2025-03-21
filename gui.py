import tkinter as tk
from PIL import Image, ImageTk

class GUI:
    def __init__(self):

        self.root = tk.Tk()
        self.root.geometry("500x500")
        self.root.title("Movie Recommender")

        self.muted = False
        self.open_mic_image = Image.open("images/microphone.png")
        self.open_mic_image.thumbnail((40,40))
        self.open_mic_image_tk = ImageTk.PhotoImage(self.open_mic_image)


        self.closed_mic_image = Image.open("images/mute.png")
        self.closed_mic_image.thumbnail((40,40))
        self.closed_mic_image_tk = ImageTk.PhotoImage(self.closed_mic_image)

        self.label = tk.Label(self.root, text="Please input your query", font=('Arial', 18))
        self.label.pack(padx=20, pady=20)

        self.textbox = tk.Text(self.root, height=3, font=('Arial', 16))
        self.textbox.pack(padx=20, pady=5)

        # Button frame
        self.buttonframe = tk.Frame(self.root)
        self.buttonframe.columnconfigure(0, weight=1)
        self.buttonframe.columnconfigure(1, weight=1)
        self.buttonframe.columnconfigure(2, weight=1)


        # Submit and Reset buttons
        self.submit_btn = tk.Button(self.buttonframe, text="Submit", font=('Arial', 14), command=self.get_message)
        self.submit_btn.grid(row=0, column=0, padx=10, pady=10)


        self.voice_btn = tk.Button(self.buttonframe, image=self.open_mic_image_tk, font=('Arial', 14), command = self.toggle_voice_control)
        self.voice_btn.grid(row=0, column=2, padx=10, pady=10)

        self.reset_btn = tk.Button(self.buttonframe, text="Reset", font=('Arial', 14), command=self.reset)
        self.reset_btn.grid(row=0, column=1, padx=10, pady=10)

        self.buttonframe.pack(pady=5, fill="x")

        # Text widget to display conversation
        self.text_display = tk.Text(self.root, font=('Arial', 14), height=10, state='disabled')
        self.text_display.pack(padx=20, pady=5, fill="both", expand=True)

        # Define tags for different backgrounds
        self.text_display.tag_configure("user_input", background="lightblue")
        self.text_display.tag_configure("response", background="lightgreen")

        self.root.mainloop()

    def get_message(self):
        self.text_display.config(state='normal') #unlock text to be created within the conversation text window

        text = self.textbox.get("1.0", "end-1c").strip()  # Get user input and remove trailing spaces
        print(text)  # Print for debugging
        if text:  # Only add if text is not empty
            # Insert user input with a background color
            self.text_display.insert(tk.END, f"User: {text}\n", "user_input")

            # Simulate a response and insert with a different background color
            response = "Response: Here's a suggestion for you."
            self.text_display.insert(tk.END, f"{response}\n", "response")

        self.text_display.config(state='disabled') #lock tex within the conversation text window to prevent the user from manually adding text

        return text

    # Method to clear the textbox
    def reset(self):
        self.textbox.delete("1.0", tk.END)
        self.text_display.delete("1.0", tk.END)


    # print responses from the conversational agent
    def response(self, res):
        self.text_display.config(state='normal') #unlock text to be created within the conversation text window
        self.text_display.insert(tk.END, f"{res}\n", "resonse")
        self.text_display.config(state='disabled') #lock tex within the conversation text window to prevent the user from manually adding text


    #enable and disable voice control
    def toggle_voice_control(self):
        if self.muted: 
            self.voice_btn.config(image=self.open_mic_image_tk)
            print("toggled off")

            #disable text control to eliminate conflicts
            self.submit_btn.config(state='disabled')  
            self.textbox.config(state='disabled')  
            self.muted = False
        else: 
            self.voice_btn.config(image=self.closed_mic_image_tk)
            print("toggled on")

            #enable text control
            self.submit_btn.config(state='normal') 
            self.textbox.config(state='normal')  
            self.muted = True


    def get_muted_status(self):
        return self.muted
