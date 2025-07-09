// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'StartLesson.dart'; // Ensure this file exists and is correctly implemented

class LessonService {
  static const String baseUrl = 'http://10.0.2.2:5000'; // Ensure this matches your backend's IP and port

  Future<List<Map<String, dynamic>>?> fetchQuestions(String hash, int lessonNumber) async {
    final uri = Uri.parse('$baseUrl/get_lesson_questions')
        .replace(queryParameters: {
      'hash': hash,
      'lesson_number': lessonNumber.toString(),
    });

    try {
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final questions = data['questions'];

        if (questions is List) {
          return questions
              .map<Map<String, dynamic>>((item) => Map<String, dynamic>.from(item))
              .toList();
        } else {
          print('Unexpected response format for questions for lesson $lessonNumber: $data');
          return null;
        }
      } else {
        print('Error fetching lesson questions for lesson $lessonNumber: Status ${response.statusCode}, Body: ${response.body}');
        return null;
      }
    } catch (e) {
      print('Network error fetching lesson questions for lesson $lessonNumber: $e');
      return null;
    }
  }
}

class LessonCirclesPage extends StatefulWidget {
  final String hash;

  LessonCirclesPage({required this.hash});

  @override
  _LessonCirclesPageState createState() => _LessonCirclesPageState();
}

class _LessonCirclesPageState extends State<LessonCirclesPage> {
  Map<int, double> _lessonData = {};
  List<int> _orderedLessonNumbers = [];

  bool isLoading = true;
  bool hasError = false;
  String errorMessage = "";

  @override
  void initState() {
    super.initState();
    print("LessonCirclesPage: Initializing with hash: ${widget.hash}");
    _fetchLessonListAndUpdateState();
  }

  Future<void> _fetchLessonListAndUpdateState() async {
    setState(() {
      isLoading = true;
      hasError = false;
      errorMessage = "";
      _lessonData.clear();
      _orderedLessonNumbers.clear();
    });

    final url = Uri.parse('http://10.0.2.2:5000/get_lessons_for_hash?hash=${widget.hash}');
    print("LessonCirclesPage: Attempting to fetch lesson list from URL: $url");

    try {
      final response = await http.get(url);
      print("LessonCirclesPage: Response Status Code: ${response.statusCode}");
      print("LessonCirclesPage: Response Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data.containsKey('lessons') && data['lessons'] is List) {
          List<int> tempOrderedNumbers = [];
          Map<int, double> tempLessonData = {};

          for (var item in data['lessons']) {
            if (item is Map<String, dynamic> && item.containsKey('lesson_number') && item.containsKey('percentage')) {
              final lessonNum = item['lesson_number'];
              final percentage = (item['percentage'] is int)
                  ? (item['percentage'] as int).toDouble()
                  : item['percentage'] as double;

              if (lessonNum is int && percentage is double) {
                tempOrderedNumbers.add(lessonNum);
                tempLessonData[lessonNum] = percentage;
              } else {
                print('Warning: Invalid type for lesson_number or percentage in item: $item');
              }
            } else {
              print('Warning: Unexpected item format in lessons list: $item');
            }
          }

          tempOrderedNumbers.sort(); // Ensure lessons are sorted

          setState(() {
            _orderedLessonNumbers = tempOrderedNumbers;
            _lessonData = tempLessonData;
            isLoading = false;
          });

          print('--- DEBUGGING LESSON DATA (After setState) ---');
          _lessonData.forEach((key, value) {
            print('Lesson $key: Percentage $value% (Type: ${value.runtimeType})');
          });
          print('Is Lesson 0 started? ${_isLessonStarted(0)}');
          print('Is Lesson 0 completed (for unlock logic)? ${_isLessonCompleted(0)}');
          print('Is Lesson 1 completed (for unlock logic)? ${_isLessonCompleted(1)}');
          print('---------------------------------------------');

        } else {
          setState(() {
            hasError = true;
            isLoading = false;
            errorMessage = "Invalid data format from server: 'lessons' key missing or not a list.";
            print("LessonCirclesPage Error: $errorMessage");
          });
        }
      } else {
        setState(() {
          hasError = true;
          isLoading = false;
          errorMessage = 'Failed to load lesson list. Status: ${response.statusCode}, Body: ${response.body}';
          print("LessonCirclesPage Error: $errorMessage");
        });
      }
    } catch (e) {
      print("LessonCirclesPage Network Error: $e");
      setState(() {
        hasError = true;
        isLoading = false;
        errorMessage = 'Network error or server unreachable: $e';
      });
    }
  }

  // Helper function to check if a lesson has started (percentage > 0.0)
  bool _isLessonStarted(int lessonNumber) {
    return _lessonData.containsKey(lessonNumber) && _lessonData[lessonNumber] != null && _lessonData[lessonNumber]! > 0.0;
  }

  // Helper function to check if a lesson is considered "completed" (percentage >= 50.0 for unlocking)
  bool _isLessonCompleted(int lessonNumber) {
    return _lessonData.containsKey(lessonNumber) && _lessonData[lessonNumber] != null && _lessonData[lessonNumber]! >= 50.0;
  }

  @override
  Widget build(BuildContext context) {
    // Determine if Lesson 0 is completed (needed for Lesson 1 unlock)
    final bool isLesson0CompletedForUnlock = _isLessonCompleted(0);
    // Determine if Lesson 0 has been started (percentage > 0.0)
    final bool isLesson0Started = _isLessonStarted(0);

    // Determine if Lesson 1 is completed (needed for Lessons 2+ unlock)
    final bool isLesson1Completed = _isLessonCompleted(1);


    return Scaffold(
      appBar: AppBar(title: Text('Lessons for ${widget.hash}')),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : hasError
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          "Error loading lessons:",
                          style: TextStyle(fontSize: 18, color: Colors.red),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 10),
                        Text(
                          errorMessage,
                          style: TextStyle(fontSize: 14, color: Colors.redAccent),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: _fetchLessonListAndUpdateState,
                          child: Text("Retry"),
                        ),
                      ],
                    ),
                  ),
                )
              : _orderedLessonNumbers.isEmpty && !isLesson0Started // No lessons fetched and Lesson 0 hasn't started
                  ? Center(
                      // This case might happen if get_lessons_for_hash returns an empty list
                      // before lesson0.json is created, or if it errors out.
                      // We still need to show Lesson 0, even if not explicitly in _orderedLessonNumbers yet.
                      // If _orderedLessonNumbers is empty, it implies lesson0 hasn't been recognized yet,
                      // so we'll simulate its presence for the initial state.
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _buildLessonCircle(
                            lessonNumber: 0,
                            actualPercentage: _lessonData.containsKey(0) ? _lessonData[0]! : 0.0,
                            isLessonAvailable: true,
                            isQuestionMark: false,
                          ),
                          SizedBox(height: 20),
                          // Display the gray question mark circle if Lesson 0 hasn't started
                          _buildQuestionMarkCircle(),
                        ],
                      ),
                    )
                  : SingleChildScrollView(
                      child: Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              // Always render Lesson 0
                              _buildLessonCircle(
                                lessonNumber: 0,
                                actualPercentage: _lessonData.containsKey(0) ? _lessonData[0]! : 0.0,
                                isLessonAvailable: true,
                                isQuestionMark: false,
                              ),
                              SizedBox(height: 10), // Spacing between lesson 0 and others/placeholder
                              // Conditional rendering for subsequent lessons or placeholder
                              if (!isLesson0Started)
                                // If Lesson 0 hasn't started (percentage 0.0), show only the question mark placeholder
                                _buildQuestionMarkCircle()
                              else
                                // If Lesson 0 has started, display all other lessons
                                ..._orderedLessonNumbers.where((ln) => ln != 0).map((lessonNumber) {
                                  final double? actualPercentage = _lessonData[lessonNumber];

                                  // --- Unlocking Logic ---
                                  bool isLessonAvailable;
                                  if (lessonNumber == 1) {
                                    isLessonAvailable = isLesson0CompletedForUnlock; // Lesson 1 unlocks if Lesson 0 is >= 50%
                                  } else {
                                    // Lessons 2 and beyond unlock if Lesson 1 is >= 50%
                                    isLessonAvailable = isLesson1Completed;
                                  }

                                  // --- Percentage Display Logic ---
                                  String displayPercentageText = '';
                                  Color displayPercentageColor;

                                  if (actualPercentage != null) {
                                      displayPercentageText = actualPercentage >= 50.0
                                          ? '${actualPercentage.toStringAsFixed(0)}%'
                                          : '0%';
                                    displayPercentageColor = isLessonAvailable ? Colors.deepOrange : Colors.grey.shade600;
                                  } else {
                                    // If percentage is null (e.g., lesson not started), show 0%
                                    displayPercentageText = '0%';
                                    displayPercentageColor = isLessonAvailable ? Colors.deepOrange : Colors.grey.shade600;
                                  }

                                  return _buildLessonCircle(
                                    lessonNumber: lessonNumber,
                                    actualPercentage: actualPercentage ?? 0.0,
                                    isLessonAvailable: isLessonAvailable,
                                    displayPercentageText: displayPercentageText,
                                    displayPercentageColor: displayPercentageColor,
                                  );
                                }).toList(),
                            ],
                          ),
                        ),
                      ),
                    ),
    );
  }

  // Helper method to build a single lesson circle widget
  Widget _buildLessonCircle({
    required int lessonNumber,
    required double actualPercentage,
    required bool isLessonAvailable,
    bool isQuestionMark = false, // Added for the question mark circle
    String? displayPercentageText, // Optional override for percentage text
    Color? displayPercentageColor, // Optional override for percentage color
  }) {
    String textToDisplay;
    Color circleColor;
    Color textColor;
    IconData? icon;

    if (isQuestionMark) {
      textToDisplay = ''; // No number for question mark circle
      circleColor = Colors.grey.shade400;
      textColor = Colors.white70;
      icon = Icons.help_outline; // Question mark icon
      displayPercentageText = ''; // No percentage for question mark
    } else {
      textToDisplay = '${lessonNumber + 1}';
      circleColor = isLessonAvailable ? Colors.deepOrangeAccent : Colors.grey.shade400;
      textColor = isLessonAvailable ? Colors.white : Colors.white70;

      // Default percentage display if not overridden
      if (displayPercentageText == null) {
         // Special handling for Lesson 0 always showing its actual percentage
        if (lessonNumber == 0) {
          displayPercentageText = '${actualPercentage.toStringAsFixed(0)}%';
        } else {
          // For other lessons, show 0% if actual percentage is less than 50, otherwise show actual
          displayPercentageText = actualPercentage >= 50.0 ? '${actualPercentage.toStringAsFixed(0)}%' : '0%';
        }
      }
      if (displayPercentageColor == null) {
        displayPercentageColor = isLessonAvailable ? Colors.deepOrange : Colors.grey.shade600;
      }
    }


    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          GestureDetector(
            onTap: isLessonAvailable && !isQuestionMark
                ? () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => StartLesson(
                          lessonNumber: lessonNumber,
                          hash: widget.hash,
                        ),
                      ),
                    );
                    _fetchLessonListAndUpdateState();
                  }
                : null,
            child: CircleAvatar(
              radius: 30,
              backgroundColor: circleColor,
              child: icon != null
                  ? Icon(icon, color: textColor, size: 30) // Display icon if available
                  : Text(
                      textToDisplay,
                      style: TextStyle(
                          color: textColor,
                          fontSize: 18,
                          fontWeight: FontWeight.bold),
                    ),
            ),
          ),
          SizedBox(width: 10),
          Text(
            displayPercentageText ?? '', // Use the overridden text or default to empty
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: displayPercentageColor),
          ),
        ],
      ),
    );
  }

  // New helper method for the gray question mark circle
  Widget _buildQuestionMarkCircle() {
    return _buildLessonCircle(
      lessonNumber: -1, // Use a dummy lesson number not used by actual lessons
      actualPercentage: 0.0,
      isLessonAvailable: false, // It's not "available" to tap for a lesson
      isQuestionMark: true,
    );
  }
}