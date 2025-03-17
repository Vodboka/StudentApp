// ignore_for_file: file_names
//The page for adding a new lesson to the server based on the material
//TODO implement logic for adding multiple documents for a lesson (maybe create Course 1 - M Lessons)
//TODO Link with backend to create 
//TODO validation (wether the lesson name already exist)

import 'package:flutter/material.dart';

class LessonPage extends StatefulWidget {
  final String testText; // Required but not displayed

  LessonPage({required this.testText});

  @override
  _LessonPageState createState() => _LessonPageState();
}

class _LessonPageState extends State<LessonPage> {
  final TextEditingController _lessonNameController = TextEditingController();
  DateTime? _selectedDate;
  String? _selectedDifficulty;

  final List<String> difficulties = ["Easy", "Medium", "Hard"];

  // Function to show date picker
  Future<void> _pickDate(BuildContext context) async {
    DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );

    if (pickedDate != null && pickedDate != _selectedDate) {
      setState(() {
        _selectedDate = pickedDate;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Add Lesson Details")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _lessonNameController,
              decoration: InputDecoration(
                labelText: "Lesson Name",
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            GestureDetector(
              onTap: () => _pickDate(context),
              child: AbsorbPointer(
                child: TextField(
                  decoration: InputDecoration(
                    labelText: _selectedDate == null
                        ? "Select Test Date"
                        : "Test Date: ${_selectedDate!.toLocal()}".split(' ')[0],
                    border: OutlineInputBorder(),
                    suffixIcon: Icon(Icons.calendar_today),
                  ),
                ),
              ),
            ),
            SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedDifficulty,
              decoration: InputDecoration(
                labelText: "Difficulty Level",
                border: OutlineInputBorder(),
              ),
              items: difficulties.map((String difficulty) {
                return DropdownMenuItem<String>(
                  value: difficulty,
                  child: Text(difficulty),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedDifficulty = value;
                });
              },
            ),
            SizedBox(height: 24),
            Center(
              child: ElevatedButton(
                onPressed: () {
                  // Handle form submission, testText is still accessible
                  print("Test Text (Hidden): ${widget.testText}");
                  print("Lesson: ${_lessonNameController.text}");
                  print("Date: $_selectedDate");
                  print("Difficulty: $_selectedDifficulty");
                },
                child: Text("Submit"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
